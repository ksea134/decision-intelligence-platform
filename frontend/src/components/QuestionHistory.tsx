"use client";

import { useState } from "react";
import { HistoryEntry } from "@/lib/api";

interface QuestionHistoryProps {
  history: HistoryEntry[];
  onRerun: (text: string) => void;
  onDelete: (entryId: string) => void;
}

export default function QuestionHistory({ history, onRerun, onDelete }: QuestionHistoryProps) {
  const [open, setOpen] = useState(false);

  if (history.length === 0) return null;

  return (
    <div className="mb-2">
      <button
        onClick={() => setOpen(!open)}
        className="text-xs text-gray-400 hover:text-gray-300 flex items-center gap-1"
      >
        <span>{open ? "▼" : "▶"}</span>
        <span>直近の質問一覧（{history.length}件）</span>
      </button>
      {open && (
        <div className="mt-1 space-y-1">
          {history.map((entry) => (
            <div key={entry.id} className="flex items-center gap-1">
              <button
                onClick={() => onRerun(entry.text)}
                className="flex-1 text-left text-xs text-[#4CDD84] hover:text-[#5FE896]
                           bg-gray-800 hover:bg-gray-700 rounded px-2 py-1.5
                           transition-colors whitespace-pre-wrap break-words"
                title={entry.ts}
              >
                ↩ {entry.text}
              </button>
              <button
                onClick={() => onDelete(entry.id)}
                className="text-xs text-gray-500 hover:text-red-400 px-1.5 py-1.5
                           bg-gray-800 hover:bg-gray-700 rounded transition-colors"
              >
                ✕
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
