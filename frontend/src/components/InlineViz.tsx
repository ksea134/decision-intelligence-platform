"use client";

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

// Chart.js のコンポーネント登録
ChartJS.register(
  CategoryScale, LinearScale, BarElement, LineElement, PointElement,
  ArcElement, Title, Tooltip, Legend,
);

export interface VizSegment {
  type: "viz";
  chart_type: "bar" | "line" | "pie";
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
        display: true,
        text: title,
        color: "rgba(255,255,255,0.9)",
        font: { size: 14 },
      },
    },
    scales: chart_type !== "pie" ? {
      x: { ticks: { color: "rgba(255,255,255,0.6)" }, grid: { color: "rgba(255,255,255,0.1)" } },
      y: { ticks: { color: "rgba(255,255,255,0.6)" }, grid: { color: "rgba(255,255,255,0.1)" } },
    } : undefined,
  };

  return (
    <div className="my-4 p-4 bg-gray-800/50 rounded-lg border border-gray-700 max-w-xl">
      {chart_type === "bar" && <Bar data={chartData} options={options} />}
      {chart_type === "line" && <Line data={chartData} options={options} />}
      {chart_type === "pie" && <Pie data={chartData} options={options} />}
    </div>
  );
}
