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
 */
export default function MessageContent({ segments, fallbackText }: MessageContentProps) {
  if (!segments || segments.length === 0) {
    return (
      <ReactMarkdown remarkPlugins={[remarkGfm]}>
        {fallbackText}
      </ReactMarkdown>
    );
  }

  return (
    <>
      {segments.map((seg, i) => {
        if (seg.type === "text" && seg.content) {
          return (
            <ReactMarkdown key={i} remarkPlugins={[remarkGfm]}>
              {seg.content}
            </ReactMarkdown>
          );
        }
        if (seg.type === "viz" && seg.chart_type && seg.labels && seg.data) {
          return (
            <InlineViz
              key={i}
              segment={seg as VizSegment}
            />
          );
        }
        return null;
      })}
    </>
  );
}
