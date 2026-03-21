"use client";

import { useState } from "react";
import { fetchDeepDive } from "@/lib/api";

interface SupplementProps {
  userPrompt: string;
  displayText: string;
  companyDisplayName: string;
  companyFolderName: string;
  onDeepDiveClick: (question: string) => void;
}

/**
 * 深掘り質問コンポーネント。
 * 思考ロジック・インフォグラフィックはChat.tsxで自動生成・表示するため、
 * このコンポーネントは深掘り質問のみを担当する。
 */
export default function Supplement({
  userPrompt,
  displayText,
  companyFolderName,
  onDeepDiveClick,
}: SupplementProps) {
  const [deepDive, setDeepDive] = useState<string[]>([]);
  const [ddLoading, setDdLoading] = useState(false);
  const [ddOpen, setDdOpen] = useState(true);

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
      {deepDive.length === 0 && (
        <button
          onClick={handleLoadDeepDive}
          disabled={ddLoading}
          className="text-xs text-gray-400 hover:text-gray-300 disabled:opacity-50 flex items-center gap-1"
        >
          <span>▶</span>
          <span>{ddLoading ? "生成中..." : "深掘り質問"}</span>
        </button>
      )}

      {deepDive.length > 0 && (
        <div className="space-y-1">
          <button
            onClick={() => setDdOpen(!ddOpen)}
            className="text-xs text-gray-400 hover:text-gray-300 flex items-center gap-1"
          >
            <span>{ddOpen ? "▼" : "▶"}</span>
            <span>深掘り質問（{deepDive.length}件）</span>
          </button>
          {ddOpen && deepDive.map((q, i) => (
            <button
              key={i}
              onClick={() => onDeepDiveClick(q)}
              className="block w-full text-left text-xs text-[#4CDD84] hover:text-[#5FE896]
                         bg-gray-800 hover:bg-gray-700 rounded px-2 py-1.5 transition-colors"
            >
              {q}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
