"use client";

import type { ConnectionState } from "@/lib/types";

interface ConnectionStatusProps {
  connection: ConnectionState;
}

export function ConnectionStatus({ connection }: ConnectionStatusProps) {
  const getStatusColor = () => {
    switch (connection.status) {
      case "connected":
        return "bg-green-500";
      case "connecting":
        return "bg-yellow-500";
      case "disconnected":
      case "error":
        return "bg-red-500";
    }
  };

  const getStatusText = () => {
    switch (connection.status) {
      case "connected":
        return "Live";
      case "connecting":
        return "Connecting...";
      case "disconnected":
        return "Disconnected";
      case "error":
        return "Error";
    }
  };

  return (
    <div className="flex items-center gap-2">
      <div className="flex items-center gap-2">
        <div
          className={`w-2 h-2 rounded-full ${getStatusColor()} ${
            connection.status === "connected" ? "pulse-dot" : ""
          }`}
        />
        <span className="text-sm text-gray-400">{getStatusText()}</span>
      </div>
      {connection.lastUpdate && connection.status === "connected" && (
        <span className="text-xs text-gray-500">
          Last update: {connection.lastUpdate.toLocaleTimeString()}
        </span>
      )}
    </div>
  );
}
