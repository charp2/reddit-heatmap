"use client";

import { useMemo, useState, useEffect, useRef, memo } from "react";
import { Group } from "@visx/group";
import { hierarchy, treemapSquarify } from "@visx/hierarchy";
import { ParentSize } from "@visx/responsive";
import { scaleLinear } from "@visx/scale";
import { treemap as d3Treemap } from "d3-hierarchy";
import type { HypeData } from "@/lib/types";

interface HeatmapProps {
  data: HypeData[];
}

interface TreemapNode {
  name: string;
  value: number;
  sentiment: number;
  mentions: number;
  velocity: number;
}

interface NodePosition {
  ticker: string;
  x: number;
  y: number;
  width: number;
  height: number;
  color: string;
  mentions: number;
  fontSize: number;
}

const MARGIN = { top: 10, left: 10, right: 10, bottom: 10 };

function getSentimentColor(sentiment: number): string {
  if (sentiment > 0.2) {
    const intensity = Math.min(sentiment, 1);
    return `rgb(${Math.round(34 + (1 - intensity) * 50)}, ${Math.round(197 - (1 - intensity) * 50)}, ${Math.round(94 - (1 - intensity) * 20)})`;
  } else if (sentiment < -0.2) {
    const intensity = Math.min(Math.abs(sentiment), 1);
    return `rgb(${Math.round(239 - (1 - intensity) * 50)}, ${Math.round(68 + (1 - intensity) * 50)}, ${Math.round(68 + (1 - intensity) * 20)})`;
  } else {
    return "#525252";
  }
}

// Memoized single tile component
const Tile = memo(function Tile({ node }: { node: NodePosition }) {
  return (
    <g
      transform={`translate(${node.x}, ${node.y})`}
      style={{ transition: "transform 400ms ease-out" }}
    >
      <rect
        width={node.width}
        height={node.height}
        fill={node.color}
        stroke="#0a0a0a"
        strokeWidth={2}
        rx={4}
        style={{ transition: "all 400ms ease-out" }}
      />
      {node.width > 40 && node.height > 40 && (
        <>
          <text
            x={node.width / 2}
            y={node.height / 2 - (node.height > 60 ? 8 : 0)}
            textAnchor="middle"
            dominantBaseline="middle"
            fill="white"
            fontSize={node.fontSize}
            fontWeight="bold"
            style={{ textShadow: "0 1px 2px rgba(0,0,0,0.5)", pointerEvents: "none" }}
          >
            {node.ticker}
          </text>
          {node.height > 60 && (
            <text
              x={node.width / 2}
              y={node.height / 2 + node.fontSize / 2 + 4}
              textAnchor="middle"
              dominantBaseline="middle"
              fill="rgba(255,255,255,0.7)"
              fontSize={Math.max(10, node.fontSize * 0.5)}
              style={{ pointerEvents: "none" }}
            >
              {node.mentions} mentions
            </text>
          )}
        </>
      )}
    </g>
  );
});

function HeatmapInner({ data, width, height }: HeatmapProps & { width: number; height: number }) {
  const innerWidth = width - MARGIN.left - MARGIN.right;
  const innerHeight = height - MARGIN.top - MARGIN.bottom;

  const nodes = useMemo(() => {
    if (data.length === 0 || innerWidth <= 0 || innerHeight <= 0) return [];

    const treeData = {
      name: "root",
      children: data.map((d) => ({
        name: d.ticker,
        value: Math.max(d.hype, 0.1),
        sentiment: d.sentiment,
        mentions: d.mentions,
        velocity: d.velocity,
      })),
    };

    const root = hierarchy<TreemapNode | { name: string; children: TreemapNode[] }>(treeData)
      .sum((d) => ("value" in d ? d.value : 0))
      .sort((a, b) => (b.value || 0) - (a.value || 0));

    const layout = d3Treemap<TreemapNode | { name: string; children: TreemapNode[] }>()
      .size([innerWidth, innerHeight])
      .tile(treemapSquarify)
      .round(true);

    layout(root);

    const maxHype = Math.max(...data.map((d) => d.hype), 1);
    const fontScale = scaleLinear({
      domain: [0, maxHype],
      range: [10, 28],
    });

    const result: NodePosition[] = [];

    root.leaves().forEach((node) => {
      const nodeWidth = (node.x1 ?? 0) - (node.x0 ?? 0);
      const nodeHeight = (node.y1 ?? 0) - (node.y0 ?? 0);

      if (nodeWidth < 20 || nodeHeight < 20) return;

      const nodeData = node.data as TreemapNode;
      const fontSize = Math.min(
        fontScale(nodeData.value || 0),
        nodeWidth / 4,
        nodeHeight / 3
      );

      result.push({
        ticker: nodeData.name,
        x: node.x0 ?? 0,
        y: node.y0 ?? 0,
        width: nodeWidth,
        height: nodeHeight,
        color: getSentimentColor(nodeData.sentiment),
        mentions: nodeData.mentions,
        fontSize,
      });
    });

    return result;
  }, [data, innerWidth, innerHeight]);

  if (data.length === 0) {
    return (
      <div className="flex items-center justify-center h-full text-gray-500">
        Waiting for data...
      </div>
    );
  }

  return (
    <svg width={width} height={height} style={{ display: "block" }}>
      <Group top={MARGIN.top} left={MARGIN.left}>
        {nodes.map((node) => (
          <Tile key={node.ticker} node={node} />
        ))}
      </Group>
    </svg>
  );
}

// Stable size wrapper to prevent re-renders from tiny size changes
function StableSizeWrapper({ data, width, height }: HeatmapProps & { width: number; height: number }) {
  const sizeRef = useRef({ width, height });
  const [, forceUpdate] = useState(0);

  // Only update if size changed significantly
  if (width > 0 && height > 0) {
    if (Math.abs(width - sizeRef.current.width) > 10 || Math.abs(height - sizeRef.current.height) > 10) {
      sizeRef.current = { width, height };
    }
  }

  const stableWidth = sizeRef.current.width || width;
  const stableHeight = sizeRef.current.height || height;

  if (stableWidth <= 0 || stableHeight <= 0) {
    return (
      <div className="flex items-center justify-center h-full text-gray-500">
        Loading...
      </div>
    );
  }

  return <HeatmapInner data={data} width={stableWidth} height={stableHeight} />;
}

export function Heatmap({ data }: HeatmapProps) {
  return (
    <div className="w-full h-full min-h-[400px]">
      <ParentSize debounceTime={150}>
        {({ width, height }) => (
          <StableSizeWrapper data={data} width={width} height={height} />
        )}
      </ParentSize>
    </div>
  );
}
