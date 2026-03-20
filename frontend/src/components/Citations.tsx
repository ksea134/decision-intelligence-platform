"use client";

import { FilesData } from "@/lib/api";

interface CitationsProps {
  files: FilesData | null;
}

export default function Citations({ files }: CitationsProps) {
  if (!files) return null;

  const { structured, unstructured } = files;
  if (structured.length === 0 && unstructured.length === 0) {
    return (
      <p className="text-xs text-yellow-500/60 mt-2">
        出典情報: AIからの戻り値なし
      </p>
    );
  }

  return (
    <div className="text-xs text-gray-400 mt-2 space-y-1">
      {structured.length > 0 && (
        <p>構造化データ: {structured.join(", ")}</p>
      )}
      {unstructured.length > 0 && (
        <p>非構造化データ: {unstructured.join(", ")}</p>
      )}
    </div>
  );
}
