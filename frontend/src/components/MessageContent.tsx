"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import InlineViz, { VizSegment } from "./InlineViz";

export interface Segment {
  type: "text" | "viz";
  content?: string;
  chart_type?: "bar" | "line" | "pie";
  title?: string;
  labels?: string[];
  data?: number[];
}

interface MessageContentProps {
  segments: Segment[] | null;
  fallbackText: string;
}

/**
 * メッセージ内容を描画する。
 * segments がある場合はテキストとチャートを交互に表示。
 * segments がない場合は fallbackText をマークダウンとして表示。
 * chat-mdクラスでStreamlit版準拠のスタイル（見出し白、太字イエロー）を適用。
 */
export default function MessageContent({ segments, fallbackText }: MessageContentProps) {
  if (!segments || segments.length === 0) {
    return (
      <div className="chat-md">
        <ReactMarkdown remarkPlugins={[remarkGfm]}>
          {fallbackText}
        </ReactMarkdown>
      </div>
    );
  }

  return (
    <div className="chat-md">
      {segments.map((seg, i) => {
        if (seg.type === "text" && seg.content) {
          return (
            <ReactMarkdown key={i} remarkPlugins={[remarkGfm]}>
              {seg.content}
            </ReactMarkdown>
          );
        }
        if (seg.type === "viz" && seg.chart_type && seg.labels && seg.data) {
          try {
            return <InlineViz key={i} segment={seg as VizSegment} />;
          } catch (e) {
            return <pre key={i} style={{color:"#f87171",fontSize:"12px"}}>[描画エラー]</pre>;
          }
        }
        return null;
      })}
    </div>
  );
}
