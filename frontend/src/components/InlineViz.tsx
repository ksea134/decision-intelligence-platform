"use client";

import dynamic from "next/dynamic";
import MermaidChart from "./MermaidChart";

// ECharts を SSR 回避で動的インポート
const ReactECharts = dynamic(() => import("echarts-for-react"), { ssr: false });

export interface VizSegment {
  type: "viz";
  chart_type: "bar" | "line" | "pie" | "mermaid";
  title: string;
  labels?: string[];
  data?: number[];
  code?: string;
}

interface InlineVizProps {
  segment: VizSegment;
}

const COLORS = [
  "#3b82f6", // blue
  "#22c55e", // green
  "#f59e0b", // amber
  "#ef4444", // red
  "#a855f7", // purple
  "#06b6d4", // cyan
  "#f97316", // orange
  "#ec4899", // pink
];

export default function InlineViz({ segment }: InlineVizProps) {
  const { chart_type, title } = segment;

  // Mermaid描画
  if (chart_type === "mermaid" && segment.code) {
    return <MermaidChart code={segment.code} title={title} />;
  }

  // ECharts描画（bar/line/pie）
  const labels = segment.labels || [];
  const data = segment.data || [];

  const option = chart_type === "pie"
    ? _buildPieOption(title, labels, data)
    : _buildCartesianOption(chart_type as "bar" | "line", title, labels, data);

  return (
    <div className="my-4 max-w-2xl mx-auto">
      <ReactECharts
        option={option}
        style={{ height: "400px", width: "100%" }}
        opts={{ renderer: "canvas" }}
        theme="dark"
      />
    </div>
  );
}

function _buildCartesianOption(
  chartType: "bar" | "line",
  title: string,
  labels: string[],
  data: number[],
) {
  return {
    backgroundColor: "transparent",
    title: {
      text: title,
      left: "center",
      textStyle: { color: "rgba(255,255,255,0.9)", fontSize: 14 },
    },
    tooltip: {
      trigger: "axis",
      backgroundColor: "rgba(30,30,30,0.95)",
      borderColor: "#4CDD84",
      textStyle: { color: "#fff" },
    },
    xAxis: {
      type: "category",
      data: labels,
      axisLabel: { color: "rgba(255,255,255,0.6)", fontSize: 11, rotate: labels.length > 6 ? 30 : 0 },
      axisLine: { lineStyle: { color: "rgba(255,255,255,0.15)" } },
    },
    yAxis: {
      type: "value",
      axisLabel: { color: "rgba(255,255,255,0.6)", fontSize: 11 },
      splitLine: { lineStyle: { color: "rgba(255,255,255,0.08)" } },
    },
    series: [
      {
        type: chartType,
        data,
        itemStyle: {
          color: chartType === "bar"
            ? {
                type: "linear",
                x: 0, y: 0, x2: 0, y2: 1,
                colorStops: [
                  { offset: 0, color: COLORS[0] },
                  { offset: 1, color: "rgba(59,130,246,0.3)" },
                ],
              }
            : COLORS[0],
          borderRadius: chartType === "bar" ? [4, 4, 0, 0] : undefined,
        },
        lineStyle: chartType === "line" ? { width: 3, color: COLORS[0] } : undefined,
        areaStyle: chartType === "line"
          ? {
              color: {
                type: "linear",
                x: 0, y: 0, x2: 0, y2: 1,
                colorStops: [
                  { offset: 0, color: "rgba(59,130,246,0.4)" },
                  { offset: 1, color: "rgba(59,130,246,0.05)" },
                ],
              },
            }
          : undefined,
        smooth: false,
        symbol: chartType === "line" ? "circle" : undefined,
        symbolSize: chartType === "line" ? 6 : undefined,
        animationDuration: 800,
        animationEasing: "cubicOut",
      },
    ],
    grid: { left: "10%", right: "5%", bottom: "15%", top: "15%" },
  };
}

function _buildPieOption(title: string, labels: string[], data: number[]) {
  const pieData = labels.map((name, i) => ({
    name,
    value: data[i],
    itemStyle: { color: COLORS[i % COLORS.length] },
  }));

  return {
    backgroundColor: "transparent",
    title: {
      text: title,
      left: "center",
      textStyle: { color: "rgba(255,255,255,0.9)", fontSize: 14 },
    },
    tooltip: {
      trigger: "item",
      backgroundColor: "rgba(30,30,30,0.95)",
      borderColor: "#4CDD84",
      textStyle: { color: "#fff" },
      formatter: "{b}: {c} ({d}%)",
    },
    legend: {
      bottom: "5%",
      textStyle: { color: "rgba(255,255,255,0.7)", fontSize: 11 },
    },
    series: [
      {
        type: "pie",
        radius: ["35%", "65%"],
        center: ["50%", "45%"],
        data: pieData,
        label: {
          color: "rgba(255,255,255,0.8)",
          fontSize: 11,
          formatter: "{b}\n{d}%",
        },
        labelLine: { lineStyle: { color: "rgba(255,255,255,0.3)" } },
        emphasis: {
          itemStyle: {
            shadowBlur: 10,
            shadowOffsetX: 0,
            shadowColor: "rgba(0,0,0,0.5)",
          },
          scale: true,
          scaleSize: 8,
        },
        animationType: "scale",
        animationDuration: 800,
        animationEasing: "cubicOut",
      },
    ],
  };
}
