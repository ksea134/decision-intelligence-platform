"use client";

import { useEffect, useRef, useState } from "react";

interface MermaidChartProps {
  code: string;
  title?: string;
}

/**
 * Mermaid記法をSVGに変換して描画するコンポーネント。
 * レンダリング失敗時はコードブロックとしてフォールバック表示する。
 */
export default function MermaidChart({ code, title }: MermaidChartProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [error, setError] = useState<string | null>(null);
  const [rendered, setRendered] = useState(false);

  useEffect(() => {
    let cancelled = false;

    async function render() {
      if (!containerRef.current || !code.trim()) return;

      try {
        // dynamic import（SSR回避）
        const mermaid = (await import("mermaid")).default;
        mermaid.initialize({
          startOnLoad: false,
          theme: "dark",
          themeVariables: {
            primaryColor: "#1e3a5f",
            primaryTextColor: "#ffffff",
            primaryBorderColor: "#4CDD84",
            lineColor: "#4CDD84",
            secondaryColor: "#0A0E14",
            tertiaryColor: "#1a1a2e",
            fontFamily: "-apple-system, BlinkMacSystemFont, sans-serif",
          },
          flowchart: { curve: "basis", padding: 15 },
        });

        const id = `mermaid-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
        const { svg } = await mermaid.render(id, code.trim());

        if (!cancelled && containerRef.current) {
          containerRef.current.innerHTML = svg;
          setRendered(true);
          setError(null);
        }
      } catch (e) {
        if (!cancelled) {
          setError(e instanceof Error ? e.message : "Mermaid描画エラー");
          setRendered(false);
        }
      }
    }

    render();
    return () => { cancelled = true; };
  }, [code]);

  return (
    <div className="my-4 p-4 bg-gray-800/50 rounded-lg border border-gray-700 max-w-2xl overflow-x-auto">
      {title && (
        <div className="text-sm font-bold text-white mb-2">{title}</div>
      )}

      {/* Mermaid SVG描画エリア */}
      <div ref={containerRef} className={error ? "hidden" : ""} />

      {/* エラー時フォールバック: コードブロック表示 */}
      {error && (
        <div>
          <div className="text-xs text-yellow-400 mb-1">フローチャートの描画に失敗しました</div>
          <pre className="text-xs text-gray-400 bg-gray-900 rounded p-3 overflow-x-auto whitespace-pre-wrap">
            {code}
          </pre>
        </div>
      )}
    </div>
  );
}
