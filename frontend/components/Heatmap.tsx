"use client";

import { useMemo } from "react";
import { Group } from "@visx/group";
import { Treemap, hierarchy, treemapSquarify, HierarchyRectangularNode } from "@visx/hierarchy";
import { ParentSize } from "@visx/responsive";
import { scaleLinear } from "@visx/scale";
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

const MARGIN = { top: 10, left: 10, right: 10, bottom: 10 };

function getSentimentColor(sentiment: number): string {
  if (sentiment > 0.2) {
    // Bullish - green shades
    const intensity = Math.min(sentiment, 1);
    return `rgb(${34 + (1 - intensity) * 50}, ${197 - (1 - intensity) * 50}, ${94 - (1 - intensity) * 20})`;
  } else if (sentiment < -0.2) {
    // Bearish - red shades
    const intensity = Math.min(Math.abs(sentiment), 1);
    return `rgb(${239 - (1 - intensity) * 50}, ${68 + (1 - intensity) * 50}, ${68 + (1 - intensity) * 20})`;
  } else {
    // Neutral - gray
    return "#525252";
  }
}

function HeatmapChart({ data, width, height }: HeatmapProps & { width: number; height: number }) {
  const innerWidth = width - MARGIN.left - MARGIN.right;
  const innerHeight = height - MARGIN.top - MARGIN.bottom;

  const root = useMemo(() => {
    const treeData = {
      name: "root",
      children: data.map((d) => ({
        name: d.ticker,
        value: Math.max(d.hype, 0.1), // Ensure minimum size
        sentiment: d.sentiment,
        mentions: d.mentions,
        velocity: d.velocity,
      })),
    };

    return hierarchy<TreemapNode | { name: string; children: TreemapNode[] }>(treeData)
      .sum((d) => ("value" in d ? d.value : 0))
      .sort((a, b) => (b.value || 0) - (a.value || 0));
  }, [data]);

  const fontScale = scaleLinear({
    domain: [0, Math.max(...data.map((d) => d.hype), 1)],
    range: [10, 32],
  });

  if (data.length === 0) {
    return (
      <div className="flex items-center justify-center h-full text-gray-500">
        Waiting for data...
      </div>
    );
  }

  return (
    <svg width={width} height={height}>
      <Treemap<TreemapNode | { name: string; children: TreemapNode[] }>
        root={root}
        size={[innerWidth, innerHeight]}
        tile={treemapSquarify}
        round
      >
        {(treemap) => (
          <Group top={MARGIN.top} left={MARGIN.left}>
            {treemap.descendants().map((node, i) => {
              const nodeWidth = node.x1 - node.x0;
              const nodeHeight = node.y1 - node.y0;

              // Skip root node and tiny nodes
              if (node.depth === 0 || nodeWidth < 30 || nodeHeight < 30) {
                return null;
              }

              const nodeData = node.data as TreemapNode;
              const color = getSentimentColor(nodeData.sentiment);
              const fontSize = Math.min(
                fontScale(nodeData.value || 0),
                nodeWidth / 4,
                nodeHeight / 3
              );

              return (
                <Group key={`node-${i}`} top={node.y0} left={node.x0}>
                  <rect
                    width={nodeWidth}
                    height={nodeHeight}
                    fill={color}
                    stroke="#0a0a0a"
                    strokeWidth={2}
                    rx={4}
                    className="treemap-tile cursor-pointer"
                  />
                  {nodeWidth > 40 && nodeHeight > 40 && (
                    <>
                      <text
                        x={nodeWidth / 2}
                        y={nodeHeight / 2 - (nodeHeight > 60 ? 8 : 0)}
                        textAnchor="middle"
                        dominantBaseline="middle"
                        fill="white"
                        fontSize={fontSize}
                        fontWeight="bold"
                        style={{ textShadow: "0 1px 2px rgba(0,0,0,0.5)" }}
                      >
                        {nodeData.name}
                      </text>
                      {nodeHeight > 60 && (
                        <text
                          x={nodeWidth / 2}
                          y={nodeHeight / 2 + fontSize / 2 + 4}
                          textAnchor="middle"
                          dominantBaseline="middle"
                          fill="rgba(255,255,255,0.7)"
                          fontSize={Math.max(10, fontSize * 0.5)}
                        >
                          {nodeData.mentions} mentions
                        </text>
                      )}
                    </>
                  )}
                </Group>
              );
            })}
          </Group>
        )}
      </Treemap>
    </svg>
  );
}

export function Heatmap({ data }: HeatmapProps) {
  return (
    <div className="w-full h-full min-h-[400px]">
      <ParentSize>
        {({ width, height }) => (
          <HeatmapChart data={data} width={width} height={height} />
        )}
      </ParentSize>
    </div>
  );
}
