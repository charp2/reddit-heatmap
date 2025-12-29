"use client";

import type { LatestMention } from "@/lib/types";

interface LiveFeedProps {
  items: LatestMention[];
}

function getSentimentClass(sentiment: number): string {
  if (sentiment > 0.2) return "sentiment-bullish";
  if (sentiment < -0.2) return "sentiment-bearish";
  return "sentiment-neutral";
}

function getSentimentEmoji(sentiment: number): string {
  if (sentiment > 0.5) return "🚀";
  if (sentiment > 0.2) return "📈";
  if (sentiment < -0.5) return "💀";
  if (sentiment < -0.2) return "📉";
  return "➖";
}

function formatTime(timestamp: string): string {
  const date = new Date(timestamp);
  return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

function truncateContent(content: string, maxLength: number = 100): string {
  if (content.length <= maxLength) return content;
  return content.substring(0, maxLength).trim() + "...";
}

export function LiveFeed({ items }: LiveFeedProps) {
  if (items.length === 0) {
    return (
      <div className="flex items-center justify-center h-full text-gray-500 py-8">
        <div className="text-center">
          <div className="text-2xl mb-2">📡</div>
          <div>Waiting for mentions...</div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-2 overflow-y-auto max-h-[500px] pr-2">
      {items.map((item, index) => (
        <div
          key={`${item.timestamp}-${index}`}
          className="feed-item bg-card border border-border rounded-lg p-3 hover:border-gray-600 transition-colors"
        >
          <div className="flex items-start justify-between gap-2 mb-1">
            <div className="flex items-center gap-2">
              <span className="font-mono font-bold text-white bg-gray-800 px-2 py-0.5 rounded">
                ${item.ticker}
              </span>
              <span className={`text-lg ${getSentimentClass(item.sentiment)}`}>
                {getSentimentEmoji(item.sentiment)}
              </span>
              <span className="text-xs text-gray-500 bg-gray-800 px-1.5 py-0.5 rounded">
                {item.content_type}
              </span>
            </div>
            <span className="text-xs text-gray-500 whitespace-nowrap">
              {formatTime(item.timestamp)}
            </span>
          </div>
          <p className="text-sm text-gray-300 leading-relaxed">
            {truncateContent(item.content)}
          </p>
          <div className="flex items-center gap-2 mt-2 text-xs text-gray-500">
            <span>r/{item.source}</span>
            <span>•</span>
            <span>u/{item.author}</span>
            <span>•</span>
            <span className={getSentimentClass(item.sentiment)}>
              {item.sentiment > 0 ? "+" : ""}
              {(item.sentiment * 100).toFixed(0)}%
            </span>
          </div>
        </div>
      ))}
    </div>
  );
}
