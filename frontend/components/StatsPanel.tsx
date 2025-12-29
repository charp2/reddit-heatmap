"use client";

import type { Stats, HypeData } from "@/lib/types";

interface StatsPanelProps {
  stats: Stats | null;
  topTickers: HypeData[];
}

function getSentimentColor(sentiment: number): string {
  if (sentiment > 0.2) return "text-green-500";
  if (sentiment < -0.2) return "text-red-500";
  return "text-gray-400";
}

function StatCard({
  label,
  value,
  subValue,
}: {
  label: string;
  value: string | number;
  subValue?: string;
}) {
  return (
    <div className="bg-card border border-border rounded-lg p-4">
      <div className="text-xs text-gray-500 uppercase tracking-wide mb-1">
        {label}
      </div>
      <div className="text-2xl font-bold text-white">{value}</div>
      {subValue && <div className="text-xs text-gray-400 mt-1">{subValue}</div>}
    </div>
  );
}

export function StatsPanel({ stats, topTickers }: StatsPanelProps) {
  const top5 = topTickers.slice(0, 5);

  return (
    <div className="space-y-4">
      {/* Quick Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <StatCard
          label="Total Mentions"
          value={stats?.total_mentions || 0}
          subValue="all time"
        />
        <StatCard
          label="Last 5 Min"
          value={stats?.mentions_last_5min || 0}
          subValue={`${stats?.velocity?.toFixed(1) || 0}/min`}
        />
        <StatCard
          label="Unique Tickers"
          value={stats?.unique_tickers || 0}
          subValue="tracked"
        />
        <StatCard
          label="Last Hour"
          value={stats?.mentions_last_hour || 0}
          subValue="mentions"
        />
      </div>

      {/* Top Trending */}
      <div className="bg-card border border-border rounded-lg p-4">
        <h3 className="text-sm font-medium text-gray-400 uppercase tracking-wide mb-3">
          Top Trending
        </h3>
        <div className="space-y-2">
          {top5.length === 0 ? (
            <div className="text-gray-500 text-sm py-4 text-center">
              No data yet...
            </div>
          ) : (
            top5.map((ticker, index) => (
              <div
                key={ticker.ticker}
                className="flex items-center justify-between py-2 border-b border-border last:border-0"
              >
                <div className="flex items-center gap-3">
                  <span className="text-gray-500 font-mono text-sm w-4">
                    {index + 1}
                  </span>
                  <span className="font-mono font-bold text-white">
                    ${ticker.ticker}
                  </span>
                </div>
                <div className="flex items-center gap-4">
                  <div className="text-right">
                    <div className="text-sm font-medium text-white">
                      {ticker.mentions}
                    </div>
                    <div className="text-xs text-gray-500">mentions</div>
                  </div>
                  <div className="text-right w-16">
                    <div
                      className={`text-sm font-medium ${getSentimentColor(
                        ticker.sentiment
                      )}`}
                    >
                      {ticker.sentiment > 0 ? "+" : ""}
                      {(ticker.sentiment * 100).toFixed(0)}%
                    </div>
                    <div className="text-xs text-gray-500">sentiment</div>
                  </div>
                  <div className="w-20">
                    <div className="h-2 bg-gray-800 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-gradient-to-r from-blue-500 to-purple-500 hype-bar"
                        style={{
                          width: `${Math.min(
                            (ticker.hype / (top5[0]?.hype || 1)) * 100,
                            100
                          )}%`,
                        }}
                      />
                    </div>
                    <div className="text-xs text-gray-500 mt-1">
                      {ticker.velocity.toFixed(1)}/min
                    </div>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
