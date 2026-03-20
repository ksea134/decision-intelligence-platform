"use client";

import { useEffect, useRef } from "react";
import { Bar, Line, Pie } from "react-chartjs-2";
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  LineElement,
  PointElement,
  ArcElement,
  Title,
  Tooltip,
  Legend,
} from "chart.js";
import mermaid from "mermaid";
import { BarChart2, TrendingUp, PieChart, GitBranch } from "lucide-react";

// Chart.js のコンポーネント登録
ChartJS.register(
  CategoryScale, LinearScale, BarElement, LineElement, PointElement,
  ArcElement, Title, Tooltip, Legend,
);

export interface VizSegment {
  type: "viz";
  chart_type: "bar" | "line" | "pie" | "flowchart";
  title: string;
  labels: string[];
  data: number[];
}

interface InlineVizProps {
  segment: VizSegment;
}

const COLORS = [
  "rgba(59, 130, 246, 0.8)",   // blue
  "rgba(34, 197, 94, 0.8)",    // green
  "rgba(245, 158, 11, 0.8)",   // amber
  "rgba(239, 68, 68, 0.8)",    // red
  "rgba(168, 85, 247, 0.8)",   // purple
  "rgba(6, 182, 212, 0.8)",    // cyan
  "rgba(249, 115, 22, 0.8)",   // orange
  "rgba(236, 72, 153, 0.8)",   // pink
];

const BORDER_COLORS = COLORS.map((c) => c.replace("0.8", "1"));

function StatItem({ label, value }: { label: string; value: string }) {
  return (
    <div className="text-xs text-gray-400">
      <span>{label}: </span>
      <span className="text-white font-medium">{value}</span>
    </div>
  );
}

function MermaidChart({ code }: { code: string }) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    mermaid.initialize({
      startOnLoad: false,
      theme: "dark",
      themeVariables: {
        primaryColor: "#4F46E5",
        primaryTextColor: "#fff",
        lineColor: "#6B7280",
        background: "transparent",
      },
    });
    if (ref.current) {
      const id = `mermaid-${Math.random().toString(36).slice(2)}`;
      mermaid.render(id, code).then(({ svg }) => {
        if (ref.current) ref.current.innerHTML = svg;
      });
    }
  }, [code]);

  return <div ref={ref} className="w-full overflow-x-auto py-2" />;
}

const TYPE_CONFIG: Record<string, { icon: typeof BarChart2; label: string }> = {
  bar: { icon: BarChart2, label: "Bar" },
  line: { icon: TrendingUp, label: "Line" },
  pie: { icon: PieChart, label: "Pie" },
  flowchart: { icon: GitBranch, label: "Flow" },
};

export default function InlineViz({ segment }: InlineVizProps) {
  const { chart_type, title, labels, data } = segment;

  const chartData = {
    labels,
    datasets: [
      {
        label: title,
        data,
        backgroundColor: chart_type === "pie" ? COLORS.slice(0, data.length) : COLORS[0],
        borderColor: chart_type === "pie" ? BORDER_COLORS.slice(0, data.length) : BORDER_COLORS[0],
        borderWidth: 1,
      },
    ],
  };

  const options = {
    responsive: true,
    plugins: {
      legend: {
        display: chart_type === "pie",
        labels: { color: "rgba(255,255,255,0.7)" },
      },
      title: {
        display: false,
      },
    },
    scales: chart_type !== "pie" && chart_type !== "flowchart" ? {
      x: { ticks: { color: "rgba(255,255,255,0.6)" }, grid: { color: "rgba(255,255,255,0.1)" } },
      y: { ticks: { color: "rgba(255,255,255,0.6)" }, grid: { color: "rgba(255,255,255,0.1)" } },
    } : undefined,
  };

  const Icon = TYPE_CONFIG[chart_type]?.icon || BarChart2;
  const typeLabel = TYPE_CONFIG[chart_type]?.label || chart_type;
  const isFlowchart = chart_type === "flowchart";

  return (
    <div className="rounded-xl border border-white/10 bg-gray-900/80 backdrop-blur-sm shadow-xl overflow-hidden max-w-2xl my-4">
      {/* ヘッダー */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-white/10">
        <div className="flex items-center gap-2">
          <Icon size={16} className="text-blue-400" />
          <span className="text-sm font-semibold text-white">{title}</span>
        </div>
        <span className="text-xs px-2 py-0.5 rounded-full bg-blue-500/20 text-blue-300 font-mono">
          {typeLabel}
        </span>
      </div>

      {/* グラフ */}
      <div className="px-4 py-3">
        {chart_type === "bar" && <Bar data={chartData} options={options} />}
        {chart_type === "line" && <Line data={chartData} options={options} />}
        {chart_type === "pie" && <Pie data={chartData} options={options} />}
        {chart_type === "flowchart" && <MermaidChart code={labels.join("\n")} />}
      </div>

      {/* フッター統計（flowchartでは非表示） */}
      {!isFlowchart && (
        <div className="flex gap-6 px-4 py-2 border-t border-white/10 bg-white/5">
          <StatItem label="最大" value={Math.max(...data).toLocaleString()} />
          <StatItem label="合計" value={data.reduce((a, b) => a + b, 0).toLocaleString()} />
          <StatItem label="件数" value={String(data.length)} />
        </div>
      )}
    </div>
  );
}
