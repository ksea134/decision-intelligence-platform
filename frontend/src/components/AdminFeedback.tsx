"use client";

import { useEffect, useState } from "react";
import { API_BASE } from "@/lib/api";

interface FeedbackEntry {
  timestamp: string;
  rating: string;
  company: string;
  comment: string;
  question: string;
}

export default function AdminFeedback() {
  const [feedback, setFeedback] = useState<FeedbackEntry[]>([]);
  const [filter, setFilter] = useState<"all" | "good" | "bad">("all");
  const [companyFilter, setCompanyFilter] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    fetch(`${API_BASE}/api/feedback/list`)
      .then((r) => r.json())
      .then((data) => {
        setFeedback(data.feedback || []);
        if (data.error) setError(data.error);
        setLoading(false);
      })
      .catch((e) => {
        setError(String(e));
        setLoading(false);
      });
  }, []);

  const companies = [...new Set(feedback.map((f) => f.company).filter(Boolean))].sort();

  const filtered = feedback.filter((f) => {
    if (filter !== "all" && f.rating !== filter) return false;
    if (companyFilter && f.company !== companyFilter) return false;
    return true;
  });

  const goodCount = feedback.filter((f) => f.rating === "good").length;
  const badCount = feedback.filter((f) => f.rating === "bad").length;

  if (loading) {
    return <div className="text-gray-400 text-sm">フィードバックを読み込み中...</div>;
  }

  if (error) {
    return (
      <div>
        <div className="text-yellow-400 text-sm mb-2">データ取得エラー: {error}</div>
        <div className="text-xs text-gray-500">BigQueryシンクにデータが溜まるまで数分かかる場合があります。</div>
      </div>
    );
  }

  return (
    <div>
      {/* サマリー */}
      <div className="flex gap-6 mb-6">
        <div className="bg-gray-800 rounded-lg px-4 py-3">
          <div className="text-2xl font-bold text-white">{feedback.length}</div>
          <div className="text-xs text-gray-400">総件数</div>
        </div>
        <div className="bg-gray-800 rounded-lg px-4 py-3">
          <div className="text-2xl font-bold text-green-400">{goodCount}</div>
          <div className="text-xs text-gray-400">👍</div>
        </div>
        <div className="bg-gray-800 rounded-lg px-4 py-3">
          <div className="text-2xl font-bold text-red-400">{badCount}</div>
          <div className="text-xs text-gray-400">👎</div>
        </div>
      </div>

      {/* フィルタ */}
      <div className="flex gap-3 mb-4">
        <select
          value={filter}
          onChange={(e) => setFilter(e.target.value as "all" | "good" | "bad")}
          className="bg-gray-800 text-white text-xs rounded px-3 py-2 border border-gray-600 focus:border-[#FF462D] focus:outline-none"
        >
          <option value="all">全て</option>
          <option value="good">👍 のみ</option>
          <option value="bad">👎 のみ</option>
        </select>
        <select
          value={companyFilter}
          onChange={(e) => setCompanyFilter(e.target.value)}
          className="bg-gray-800 text-white text-xs rounded px-3 py-2 border border-gray-600 focus:border-[#FF462D] focus:outline-none"
        >
          <option value="">全企業</option>
          {companies.map((c) => (
            <option key={c} value={c}>{c}</option>
          ))}
        </select>
        <span className="text-xs text-gray-500 self-center">{filtered.length}件表示</span>
      </div>

      {/* 一覧 */}
      {filtered.length === 0 ? (
        <div className="text-gray-500 text-sm">フィードバックデータがありません。</div>
      ) : (
        <div className="space-y-2">
          {filtered.map((f, i) => (
            <div key={i} className="border border-gray-800 rounded-lg px-4 py-3">
              <div className="flex items-center gap-3 mb-1">
                <span className={f.rating === "good" ? "text-green-400" : "text-red-400"}>
                  {f.rating === "good" ? "👍" : "👎"}
                </span>
                <span className="text-xs text-gray-500">{f.timestamp ? new Date(f.timestamp).toLocaleString("ja-JP") : ""}</span>
                <span className="text-xs text-gray-600">{f.company}</span>
              </div>
              <div className="text-sm text-gray-200 mb-1">質問: {f.question}</div>
              {f.comment && (
                <div className="text-sm text-yellow-300 bg-gray-800 rounded px-3 py-2 mt-1">
                  コメント: {f.comment}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
