"use client";

import { memo, useMemo } from "react";
import { useWebSocket } from "@/hooks/useWebSocket";
import { Heatmap } from "@/components/Heatmap";
import { LiveFeed } from "@/components/LiveFeed";
import { StatsPanel } from "@/components/StatsPanel";
import { ConnectionStatus } from "@/components/ConnectionStatus";
import type { HypeData, LatestMention, Stats, ConnectionState } from "@/lib/types";

// Memoized components to prevent re-renders
const MemoizedHeatmap = memo(Heatmap);
const MemoizedLiveFeed = memo(LiveFeed);
const MemoizedStatsPanel = memo(StatsPanel);
const MemoizedConnectionStatus = memo(ConnectionStatus);

interface HeaderProps {
  connection: ConnectionState;
}

const Header = memo(function Header({ connection }: HeaderProps) {
  return (
    <header className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-6">
      <div>
        <h1 className="text-2xl md:text-3xl font-bold text-white">
          Reddit Stock Heatmap
        </h1>
        <p className="text-gray-400 text-sm mt-1">
          Real-time stock hype tracking from r/wallstreetbets, r/stocks,
          r/options
        </p>
      </div>
      <MemoizedConnectionStatus connection={connection} />
    </header>
  );
});

const DemoBanner = memo(function DemoBanner() {
  return (
    <div className="demo-banner text-black text-center py-2 px-4 rounded-lg mb-4 font-medium text-sm">
      🎭 DEMO MODE - Using simulated data. Set Reddit API credentials for live data.
    </div>
  );
});

const Legend = memo(function Legend() {
  return (
    <div className="flex items-center justify-center gap-6 mt-4 text-xs text-gray-500">
      <div className="flex items-center gap-2">
        <div className="w-4 h-4 rounded bg-red-500" />
        <span>Bearish</span>
      </div>
      <div className="flex items-center gap-2">
        <div className="w-4 h-4 rounded bg-gray-500" />
        <span>Neutral</span>
      </div>
      <div className="flex items-center gap-2">
        <div className="w-4 h-4 rounded bg-green-500" />
        <span>Bullish</span>
      </div>
    </div>
  );
});

export default function Home() {
  const { heatmapData, feedItems, stats, connection } = useWebSocket();

  // Memoize data arrays to prevent unnecessary child re-renders
  const stableHeatmapData = useMemo(() => heatmapData, [JSON.stringify(heatmapData)]);
  const stableFeedItems = useMemo(() => feedItems, [JSON.stringify(feedItems.slice(0, 10))]);
  const stableStats = useMemo(() => stats, [JSON.stringify(stats)]);

  const showDemoBanner = connection.demoMode && connection.status === "connected";

  return (
    <main className="min-h-screen p-4 md:p-6 lg:p-8">
      {showDemoBanner && <DemoBanner />}

      <Header connection={connection} />

      {/* Stats Panel */}
      <section className="mb-6">
        <MemoizedStatsPanel stats={stableStats} topTickers={stableHeatmapData} />
      </section>

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Heatmap */}
        <section className="lg:col-span-2">
          <div className="bg-card border border-border rounded-lg p-4">
            <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
              <span>Hype Heatmap</span>
              <span className="text-xs text-gray-500 font-normal">
                Size = Hype Score, Color = Sentiment
              </span>
            </h2>
            <div className="h-[500px]">
              <MemoizedHeatmap data={stableHeatmapData} />
            </div>
            <Legend />
          </div>
        </section>

        {/* Live Feed */}
        <section className="lg:col-span-1">
          <div className="bg-card border border-border rounded-lg p-4">
            <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
              <span className="w-2 h-2 bg-red-500 rounded-full pulse-dot" />
              <span>Live Feed</span>
            </h2>
            <MemoizedLiveFeed items={stableFeedItems} />
          </div>
        </section>
      </div>

      {/* Footer */}
      <footer className="mt-8 text-center text-gray-500 text-sm">
        <p>
          Data from Reddit API • Sentiment analysis via VADER •{" "}
          {connection.demoMode ? "Demo Mode" : "Live Mode"}
        </p>
      </footer>
    </main>
  );
}
