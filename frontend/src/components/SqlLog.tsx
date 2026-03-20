"use client";

import { useState } from "react";

interface SqlLogProps {
  sqlQuery: string;
  rowCount: number;
}

export default function SqlLog({ sqlQuery, rowCount }: SqlLogProps) {
  const [open, setOpen] = useState(false);

  if (!sqlQuery) return null;

  return (
    <div className="mt-2">
      <button
        onClick={() => setOpen(!open)}
        className="text-xs text-gray-400 hover:text-gray-300 flex items-center gap-1"
      >
        <span>{open ? "▼" : "▶"}</span>
        <span>BigQuery 実行ログ — 実データ（{rowCount}件取得）</span>
      </button>
      {open && (
        <div className="mt-1 space-y-2">
          <pre className="bg-gray-800 rounded p-2 text-xs text-gray-300 overflow-x-auto">
            {sqlQuery}
          </pre>
          <div className="flex gap-4 text-xs text-gray-400">
            <span>取得件数: <strong className="text-white">{rowCount} 件</strong></span>
            <span>データ種別: <strong className="text-green-400">実データ（BigQuery接続済み）</strong></span>
          </div>
        </div>
      )}
    </div>
  );
}
