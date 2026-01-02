export interface HypeData {
  ticker: string;
  hype: number;
  sentiment: number;
  mentions: number;
  velocity: number;
}

export interface LatestMention {
  ticker: string;
  content: string;
  sentiment: number;
  source: string;
  author: string;
  content_type: "post" | "comment";
  timestamp: string;
  score: number;
}

export interface Stats {
  total_mentions: number;
  unique_tickers: number;
  mentions_last_5min: number;
  mentions_last_hour: number;
  velocity: number;
}

export interface WebSocketMessage {
  type: "init" | "update";
  data: {
    heatmap: HypeData[];
    latest?: LatestMention;
    stats: Stats;
  };
  demo_mode: boolean;
  timestamp: string;
}

export interface ConnectionState {
  status: "connecting" | "connected" | "disconnected" | "error";
  lastUpdate: Date | null;
  demoMode: boolean;
}
