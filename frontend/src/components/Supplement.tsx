"use client";

import { useState } from "react";
import { fetchSupplement, fetchDeepDive, SupplementResult } from "@/lib/api";

interface SupplementProps {
  userPrompt: string;
  displayText: string;
  companyDisplayName: string;
  companyFolderName: string;
  onDeepDiveClick: (question: string) => void;
}

export default function Supplement({
  userPrompt,
  displayText,
  companyDisplayName,
  companyFolderName,
  onDeepDiveClick,
}: SupplementProps) {
  const [supplement, setSupplement] = useState<SupplementResult | null>(null);
  const [deepDive, setDeepDive] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [ddLoading, setDdLoading] = useState(false);

  const handleLoadSupplement = async () => {
    setLoading(true);
    const result = await fetchSupplement({
      user_prompt: userPrompt,
      display_text: displayText,
      company_display_name: companyDisplayName,
      company_folder_name: companyFolderName,
    });
    setSupplement(result);
    setLoading(false);
  };

  const handleLoadDeepDive = async () => {
    setDdLoading(true);
    const result = await fetchDeepDive({
      user_prompt: userPrompt,
      display_text: displayText,
      company_folder_name: companyFolderName,
    });
    setDeepDive(result.questions || []);
    setDdLoading(false);
  };

  return (
    <div className="mt-3 space-y-2">
      {/* 思考ロジック + インフォグラフィック */}
      {!supplement && (
        <button
          onClick={handleLoadSupplement}
          disabled={loading}
          className="text-xs text-blue-400 hover:text-blue-300 disabled:opacity-50"
        >
          {loading ? "生成中..." : "💡 思考ロジック・インフォグラフィックを表示"}
        </button>
      )}

      {supplement && !supplement.error && (
        <>
          {/* 思考ロジック */}
          {supplement.thought_process && (
            <details className="group">
              <summary className="text-xs text-gray-400 cursor-pointer hover:text-gray-300">
                🧠 思考ロジック
              </summary>
              <div className="mt-1 text-xs text-gray-300 bg-gray-800/50 rounded p-3 whitespace-pre-wrap">
                {supplement.thought_process}
              </div>
            </details>
          )}

          {/* インフォグラフィック */}
          {supplement.infographic_html && (
            <details className="group">
              <summary className="text-xs text-gray-400 cursor-pointer hover:text-gray-300">
                🎨 インフォグラフィック
              </summary>
              <div
                className="mt-1 bg-white rounded p-3 text-sm"
                dangerouslySetInnerHTML={{ __html: supplement.infographic_html }}
              />
            </details>
          )}
        </>
      )}

      {/* 深掘り質問 */}
      {deepDive.length === 0 && (
        <button
          onClick={handleLoadDeepDive}
          disabled={ddLoading}
          className="text-xs text-blue-400 hover:text-blue-300 disabled:opacity-50"
        >
          {ddLoading ? "生成中..." : "🔍 深掘り質問を表示"}
        </button>
      )}

      {deepDive.length > 0 && (
        <div className="space-y-1">
          <span className="text-xs text-gray-400">🔍 深掘り質問</span>
          {deepDive.map((q, i) => (
            <button
              key={i}
              onClick={() => onDeepDiveClick(q)}
              className="block w-full text-left text-xs text-blue-300 hover:text-blue-200
                         bg-gray-800/50 rounded px-3 py-2 hover:bg-gray-700/50 transition-colors"
            >
              {q}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
