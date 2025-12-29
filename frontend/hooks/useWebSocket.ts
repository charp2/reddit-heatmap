"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import type {
  HypeData,
  LatestMention,
  Stats,
  WebSocketMessage,
  ConnectionState,
} from "@/lib/types";

const WS_URL = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000/ws";
const RECONNECT_DELAY = 3000;
const MAX_FEED_ITEMS = 50;

interface UseWebSocketReturn {
  heatmapData: HypeData[];
  feedItems: LatestMention[];
  stats: Stats | null;
  connection: ConnectionState;
}

export function useWebSocket(): UseWebSocketReturn {
  const [heatmapData, setHeatmapData] = useState<HypeData[]>([]);
  const [feedItems, setFeedItems] = useState<LatestMention[]>([]);
  const [stats, setStats] = useState<Stats | null>(null);
  const [connection, setConnection] = useState<ConnectionState>({
    status: "connecting",
    lastUpdate: null,
    demoMode: false,
  });

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  const connect = useCallback(() => {
    // Clean up existing connection
    if (wsRef.current) {
      wsRef.current.close();
    }

    setConnection((prev) => ({ ...prev, status: "connecting" }));

    const ws = new WebSocket(WS_URL);
    wsRef.current = ws;

    ws.onopen = () => {
      console.log("WebSocket connected");
      setConnection((prev) => ({
        ...prev,
        status: "connected",
        lastUpdate: new Date(),
      }));
    };

    ws.onmessage = (event) => {
      try {
        const message: WebSocketMessage = JSON.parse(event.data);

        setConnection((prev) => ({
          ...prev,
          lastUpdate: new Date(),
          demoMode: message.demo_mode,
        }));

        // Update heatmap data
        if (message.data.heatmap) {
          setHeatmapData(message.data.heatmap);
        }

        // Update stats
        if (message.data.stats) {
          setStats(message.data.stats);
        }

        // Add new mention to feed
        if (message.type === "update" && message.data.latest) {
          setFeedItems((prev) => {
            const newItems = [message.data.latest!, ...prev];
            return newItems.slice(0, MAX_FEED_ITEMS);
          });
        }
      } catch (error) {
        console.error("Failed to parse WebSocket message:", error);
      }
    };

    ws.onclose = () => {
      console.log("WebSocket disconnected");
      setConnection((prev) => ({ ...prev, status: "disconnected" }));

      // Auto-reconnect
      reconnectTimeoutRef.current = setTimeout(() => {
        console.log("Attempting to reconnect...");
        connect();
      }, RECONNECT_DELAY);
    };

    ws.onerror = (error) => {
      console.error("WebSocket error:", error);
      setConnection((prev) => ({ ...prev, status: "error" }));
    };
  }, []);

  useEffect(() => {
    connect();

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
    };
  }, [connect]);

  return {
    heatmapData,
    feedItems,
    stats,
    connection,
  };
}
