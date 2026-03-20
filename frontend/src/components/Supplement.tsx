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
          className="text-xs text-blue-400 hover:text-blue-300 disabled:opacity-50"
        >
          {ddLoading ? "生成中..." : "深掘り質問を表示"}
        </button>
      )}

      {deepDive.length > 0 && (
        <div className="space-y-1">
          <span className="text-xs text-gray-400">深掘り質問</span>
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
