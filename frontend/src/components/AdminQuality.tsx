"use client";

import React, { useEffect, useState } from "react";
import { API_BASE } from "@/lib/api";
import AdminQualityDetail from "./AdminQualityDetail";

interface TraceData {
  _timestamp?: string;
  trace_id?: string;
  who?: { user: string; company: string; source: string };
  what?: { question: string; response_length: number; response_status: string; charts: string[]; sources_referenced: string[] };
  pipeline?: { total_seconds: number; steps: { step: string; seconds: number; status: string; detail: string }[] };
  agent?: { engine: string; router_model: string; selected_agent: string; agent_model: string; agent_seconds: number };
  api_calls?: number;
  quality_scores?: { citation_score: number; length_score: number; data_ref_score: number; coherence_score: number; overall_score: number };
  error?: { step: string; type: string; message: string } | null;
}

interface Summary {
  total_requests: number;
  success: number;
  errors: number;
  error_rate: number;
  avg_elapsed: number;
  p95_elapsed: number;
  quality_score: number;
  good_count: number;
  bad_count: number;
}

export default function AdminQuality() {
  const [summary, setSummary] = useState<Summary | null>(null);
  const [traces, setTraces] = useState<TraceData[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [companyFilter, setCompanyFilter] = useState("");
  const [engineFilter, setEngineFilter] = useState("");
  const [userFilter, setUserFilter] = useState("");
  const [expandedTrace, setExpandedTrace] = useState<number | null>(null);
  const [offset, setOffset] = useState(0);
  const [hasMore, setHasMore] = useState(false);

  const fetchData = (newOffset: number, append: boolean = false) => {
    setLoading(true);
    const params = new URLSearchParams({ offset: String(newOffset), limit: "50" });
    if (companyFilter) params.set("company", companyFilter);
    if (engineFilter) params.set("engine", engineFilter);
    if (userFilter) params.set("user", userFilter);

    fetch(`${API_BASE}/api/quality/metrics?${params}`)
      .then((r) => r.json())
      .then((data) => {
        setSummary(data.summary);
        setTraces(append ? [...traces, ...(data.traces || [])] : (data.traces || []));
        setHasMore(data.has_more || false);
        if (data.error) setError(data.error);
        setLoading(false);
      })
      .catch((e) => { setError(String(e)); setLoading(false); });
  };

  useEffect(() => { fetchData(0); }, [companyFilter, engineFilter, userFilter]);

  const handleLoadMore = () => {
    const newOffset = offset + 50;
    setOffset(newOffset);
    fetchData(newOffset, true);
  };

  const companies = [...new Set(traces.map((t) => t.who?.company).filter(Boolean))].sort();
  const engines = [...new Set(traces.map((t) => t.agent?.engine).filter(Boolean))].sort();
  const users = [...new Set(traces.map((t) => t.who?.user).filter(Boolean))].sort();

  const getStepTime = (t: TraceData, stepName: string): string => {
    const step = t.pipeline?.steps?.find((s) => s.step === stepName);
    return step ? `${step.seconds}s` : "-";
  };

  const getAgentLabel = (t: TraceData): string => {
    const agent = t.agent?.selected_agent || "";
    const labels: Record<string, string> = {
      analysis_agent: "分析", comparison_agent: "比較",
      forecast_agent: "予測", general_agent: "汎用",
      "要因分析エージェント": "分析", "比較分析エージェント": "比較",
      "予測分析エージェント": "予測", "汎用回答エージェント": "汎用",
      "ルーターエージェント": "ルータ",
    };
    return labels[agent] || agent || "-";
  };

  const handleCsvDownload = () => {
    const header = "時刻,種別,企業,ユーザー,合計(s),読込(s),検索(s),選択(s),BQ(s),Agent,生成(s),思考(s),図表(s),API回数,品質スコア,出典,回答長,データ参照,一貫性,エンジン,状態,質問,チャート,データソース";
    const rows = traces.map((t) => {
      const ts = t._timestamp ? new Date(t._timestamp).toLocaleString("ja-JP") : "";
      const getStep = (name: string) => t.pipeline?.steps?.find((s) => s.step === name)?.seconds ?? "";
      return [
        ts,
        t.agent?.engine === "supplement" ? "補足" : "本文",
        t.who?.company || "",
        t.who?.user || "",
        t.pipeline?.total_seconds || "",
        getStep("data_load"),
        getStep("past_qa_search"),
        getStep("table_select"),
        getStep("bq_fetch"),
        t.agent?.selected_agent || "",
        getStep("llm_generate"),
        getStep("thought_process"),
        getStep("infographic"),
        t.api_calls || "",
        t.quality_scores?.overall_score ?? "",
        t.quality_scores?.citation_score ?? "",
        t.quality_scores?.length_score ?? "",
        t.quality_scores?.data_ref_score ?? "",
        t.quality_scores?.coherence_score ?? "",
        t.agent?.engine || "",
        t.what?.response_status || "",
        `"${(t.what?.question || "").replace(/"/g, '""')}"`,
        (t.what?.charts || []).join(";"),
        (t.what?.sources_referenced || []).join(";"),
      ].join(",");
    });
    const csv = "\uFEFF" + header + "\n" + rows.join("\n");
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    const now = new Date();
    a.download = `dip_quality_log_${now.getFullYear()}${String(now.getMonth()+1).padStart(2,"0")}${String(now.getDate()).padStart(2,"0")}.csv`;
    a.click();
    URL.revokeObjectURL(a.href);
  };

  if (loading && traces.length === 0) return <div className="text-gray-400 text-sm">品質データを読み込み中...</div>;

  return (
    <div>
      {error && <div className="text-yellow-400 text-xs mb-2">⚠ {error}</div>}

      {/* サマリー */}
      {summary && (
        <div className="flex flex-wrap gap-3 mb-4">
          <div className="bg-gray-800 rounded px-3 py-2">
            <span className="text-lg font-bold text-white">{summary.total_requests}</span>
            <span className="text-[10px] text-gray-400 ml-1">件</span>
          </div>
          <div className="bg-gray-800 rounded px-3 py-2">
            <span className="text-lg font-bold text-blue-400">{summary.avg_elapsed}s</span>
            <span className="text-[10px] text-gray-400 ml-1">平均</span>
          </div>
          <div className="bg-gray-800 rounded px-3 py-2">
            <span className="text-lg font-bold text-yellow-400">{summary.p95_elapsed}s</span>
            <span className="text-[10px] text-gray-400 ml-1">P95</span>
          </div>
          <div className="bg-gray-800 rounded px-3 py-2">
            <span className={`text-lg font-bold ${summary.error_rate > 5 ? "text-red-400" : "text-green-400"}`}>{summary.error_rate}%</span>
            <span className="text-[10px] text-gray-400 ml-1">エラー</span>
          </div>
          <div className="bg-gray-800 rounded px-3 py-2">
            <span className="text-lg font-bold text-green-400">{summary.quality_score}%</span>
            <span className="text-[10px] text-gray-400 ml-1">品質（👍{summary.good_count}/👎{summary.bad_count}）</span>
          </div>
        </div>
      )}

      {/* フィルタ */}
      <div className="flex gap-2 mb-3">
        <select value={companyFilter} onChange={(e) => { setCompanyFilter(e.target.value); setOffset(0); }}
          className="bg-gray-800 text-white text-xs rounded px-2 py-1.5 border border-gray-600 focus:border-[#FF462D] focus:outline-none">
          <option value="">全企業</option>
          {companies.map((c) => <option key={c} value={c}>{c}</option>)}
        </select>
        <select value={engineFilter} onChange={(e) => { setEngineFilter(e.target.value); setOffset(0); }}
          className="bg-gray-800 text-white text-xs rounded px-2 py-1.5 border border-gray-600 focus:border-[#FF462D] focus:outline-none">
          <option value="">全エンジン</option>
          {engines.map((e) => <option key={e} value={e}>{e}</option>)}
        </select>
        <select value={userFilter} onChange={(e) => { setUserFilter(e.target.value); setOffset(0); }}
          className="bg-gray-800 text-white text-xs rounded px-2 py-1.5 border border-gray-600 focus:border-[#FF462D] focus:outline-none">
          <option value="">全ユーザー</option>
          {users.map((u) => <option key={u} value={u}>{u}</option>)}
        </select>
        <button
          onClick={handleCsvDownload}
          className="text-xs text-gray-400 hover:text-white bg-gray-800 hover:bg-gray-700 px-3 py-1.5 rounded transition-colors ml-auto"
        >
          CSVダウンロード
        </button>
      </div>

      {/* ログテーブル */}
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="text-gray-400 border-b border-gray-700">
              <th className="text-left py-2 px-2">時刻</th>
              <th className="text-left py-2 px-2">種別</th>
              <th className="text-left py-2 px-2">企業</th>
              <th className="text-left py-2 px-2">ユーザー</th>
              <th className="text-right py-2 px-2">合計</th>
              <th className="text-right py-2 px-2">読込</th>
              <th className="text-right py-2 px-2">検索</th>
              <th className="text-right py-2 px-2">選択</th>
              <th className="text-right py-2 px-2">BQ</th>
              <th className="text-right py-2 px-2 min-w-[3rem]">Agt</th>
              <th className="text-right py-2 px-2">生成</th>
              <th className="text-right py-2 px-2">思考</th>
              <th className="text-right py-2 px-2">図表</th>
              <th className="text-right py-2 px-2">API</th>
              <th className="text-right py-2 px-2">出典</th>
              <th className="text-right py-2 px-2">回答長</th>
              <th className="text-right py-2 px-2">参照</th>
              <th className="text-right py-2 px-2">一貫性</th>
              <th className="text-right py-2 px-2">総合</th>
              <th className="text-center py-2 px-2">状態</th>
            </tr>
          </thead>
          <tbody>
            {traces.map((t, i) => {
              const ts = t._timestamp ? new Date(t._timestamp).toLocaleString("ja-JP") : "";
              const total = t.pipeline?.total_seconds || 0;
              const isError = t.what?.response_status !== "success";
              return (<React.Fragment key={i}>
                <tr key={i} onClick={() => setExpandedTrace(expandedTrace === i ? null : i)}
                  className={`border-b border-gray-800 cursor-pointer hover:bg-gray-800/50 transition-colors ${isError ? "bg-red-900/10" : ""}`}>
                  <td className="py-2 px-2 text-gray-500 whitespace-nowrap">{ts}</td>
                  <td className="py-2 px-2">
                    {t.agent?.engine === "supplement"
                      ? <span className="text-[10px] text-purple-400 bg-purple-900/20 px-1.5 py-0.5 rounded">補足</span>
                      : t.agent?.engine === "v1"
                        ? <span className="text-[10px] text-green-400 bg-green-900/20 px-1.5 py-0.5 rounded">V1</span>
                        : t.agent?.engine === "adk"
                          ? <span className="text-[10px] text-blue-400 bg-blue-900/20 px-1.5 py-0.5 rounded">ADK</span>
                          : <span className="text-[10px] text-gray-400 bg-gray-900/20 px-1.5 py-0.5 rounded">-</span>
                    }
                  </td>
                  <td className="py-2 px-2 text-gray-300 truncate max-w-[120px]">{t.who?.company || ""}</td>
                  <td className="py-2 px-2 text-gray-500 truncate max-w-[100px]">{t.who?.user || ""}</td>
                  <td className={`py-2 px-2 text-right font-mono ${total > 30 ? "text-red-400" : total > 15 ? "text-yellow-400" : "text-blue-400"}`}>{total}s</td>
                  <td className="py-2 px-2 text-right text-gray-500 font-mono">{getStepTime(t, "data_load")}</td>
                  <td className="py-2 px-2 text-right text-gray-500 font-mono">{getStepTime(t, "past_qa_search")}</td>
                  <td className="py-2 px-2 text-right text-gray-500 font-mono">{getStepTime(t, "table_select")}</td>
                  <td className="py-2 px-2 text-right text-gray-500 font-mono">{getStepTime(t, "bq_fetch")}</td>
                  <td className="py-2 px-2 text-gray-400 text-right">{getAgentLabel(t)}</td>
                  <td className="py-2 px-2 text-right text-gray-500 font-mono">{getStepTime(t, "llm_generate")}</td>
                  <td className="py-2 px-2 text-right text-gray-500 font-mono">{getStepTime(t, "thought_process")}</td>
                  <td className="py-2 px-2 text-right text-gray-500 font-mono">{getStepTime(t, "infographic")}</td>
                  <td className="py-2 px-2 text-right text-gray-500 font-mono">{t.api_calls !== undefined && t.api_calls !== null ? t.api_calls : "-"}</td>
                  <td className="py-2 px-2 text-right text-gray-500 font-mono">{t.quality_scores?.citation_score ?? "-"}</td>
                  <td className="py-2 px-2 text-right text-gray-500 font-mono">{t.quality_scores?.length_score ?? "-"}</td>
                  <td className="py-2 px-2 text-right text-gray-500 font-mono">{t.quality_scores?.data_ref_score ?? "-"}</td>
                  <td className="py-2 px-2 text-right text-gray-500 font-mono">{(t.quality_scores?.coherence_score ?? -1) >= 0 ? t.quality_scores?.coherence_score : "-"}</td>
                  <td className={`py-2 px-2 text-right font-bold ${
                    (t.quality_scores?.overall_score ?? -1) >= 80 ? "text-green-400" :
                    (t.quality_scores?.overall_score ?? -1) >= 50 ? "text-yellow-400" :
                    (t.quality_scores?.overall_score ?? -1) >= 0 ? "text-red-400" : "text-gray-500"
                  }`}>{t.quality_scores?.overall_score !== undefined && t.quality_scores.overall_score >= 0 ? t.quality_scores.overall_score : "-"}</td>
                  <td className="py-2 px-2 text-center">{isError ? "❌" : "✅"}</td>
                </tr>
                {expandedTrace === i && (
                  <tr>
                    <td colSpan={99} className="p-0">
                      <AdminQualityDetail trace={t} />
                    </td>
                  </tr>
                )}
              </React.Fragment>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* もっと読み込む */}
      {hasMore && (
        <div className="text-center mt-4">
          <button
            onClick={handleLoadMore}
            disabled={loading}
            className="text-xs text-gray-400 hover:text-white bg-gray-800 hover:bg-gray-700 px-4 py-2 rounded transition-colors disabled:opacity-50"
          >
            {loading ? "読み込み中..." : "もっと読み込む（50件）"}
          </button>
        </div>
      )}

      {traces.length === 0 && !loading && (
        <div className="text-gray-500 text-sm text-center py-8">リクエストデータがありません</div>
      )}
    </div>
  );
}
