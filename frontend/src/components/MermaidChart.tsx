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

  useEffect(() => {
    let cancelled = false;

    async function render() {
      if (!containerRef.current || !code.trim()) return;

      try {
        const mermaid = (await import("mermaid")).default;
        mermaid.initialize({
          startOnLoad: false,
          suppressErrorRendering: true,
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

        // 既存のエラー要素をクリア
        containerRef.current.innerHTML = "";

        const id = `m${Date.now()}${Math.random().toString(36).slice(2, 6)}`;

        // parse で事前にバリデーション
        const valid = await mermaid.parse(code.trim(), { suppressErrors: true });
        if (!valid) {
          if (!cancelled) setError("Mermaid記法が不正です");
          return;
        }

        const { svg } = await mermaid.render(id, code.trim());

        if (!cancelled && containerRef.current) {
          containerRef.current.innerHTML = svg;
          setError(null);
        }
      } catch (e) {
        if (!cancelled) {
          setError(e instanceof Error ? e.message : "Mermaid描画エラー");
        }
      }
    }

    render();
    return () => { cancelled = true; };
  }, [code]);

  return (
    <div className="my-4 max-w-2xl mx-auto overflow-x-auto">
      {title && (
        <div className="text-sm font-bold text-white mb-2">{title}</div>
      )}

      {/* Mermaid SVG描画エリア */}
      <div ref={containerRef} className={error ? "hidden" : "flex justify-center"} />

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
