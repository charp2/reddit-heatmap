"use client";

import { useState, useEffect, useRef } from "react";
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
  // Start with empty state
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
  const lastMentionKeyRef = useRef<string | null>(null);
  const mountedRef = useRef(true);

  useEffect(() => {
    mountedRef.current = true;

    const connect = () => {
      // Clean up existing connection
      if (wsRef.current) {
        wsRef.current.close();
      }

      if (!mountedRef.current) return;

      setConnection(prev => ({ ...prev, status: "connecting" }));

      const ws = new WebSocket(WS_URL);
      wsRef.current = ws;

      ws.onopen = () => {
        if (!mountedRef.current) return;
        setConnection(prev => ({
          ...prev,
          status: "connected",
          lastUpdate: new Date(),
        }));
      };

      ws.onmessage = (event) => {
        if (!mountedRef.current) return;

        try {
          const message: WebSocketMessage = JSON.parse(event.data);

          // Update connection state
          setConnection(prev => ({
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

          // Add to feed (with duplicate prevention)
          if (message.data.latest) {
            const mentionKey = `${message.data.latest.ticker}-${message.data.latest.timestamp}`;
            if (mentionKey !== lastMentionKeyRef.current) {
              lastMentionKeyRef.current = mentionKey;
              setFeedItems(prev => [message.data.latest!, ...prev].slice(0, MAX_FEED_ITEMS));
            }
          }
        } catch (error) {
          console.error("Failed to parse WebSocket message:", error);
        }
      };

      ws.onclose = () => {
        if (!mountedRef.current) return;
        setConnection(prev => ({ ...prev, status: "disconnected" }));
        reconnectTimeoutRef.current = setTimeout(connect, RECONNECT_DELAY);
      };

      ws.onerror = () => {
        if (!mountedRef.current) return;
        setConnection(prev => ({ ...prev, status: "error" }));
      };
    };

    connect();

    return () => {
      mountedRef.current = false;
      if (wsRef.current) {
        wsRef.current.close();
      }
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
    };
  }, []);

  return { heatmapData, feedItems, stats, connection };
}
