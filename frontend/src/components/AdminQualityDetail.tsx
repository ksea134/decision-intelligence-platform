"use client";

interface TraceData {
  _timestamp?: string;
  trace_id?: string;
  who?: { user: string; company: string; source: string };
  what?: { question: string; response_length: number; response_status: string; charts: string[]; sources_referenced: string[] };
  pipeline?: { total_seconds: number; steps: { step: string; seconds: number; status: string; detail: string }[] };
  agent?: { engine: string; router_model: string; selected_agent: string; agent_model: string; agent_seconds: number };
  api_calls?: number;
  error?: { step: string; type: string; message: string } | null;
}

interface Props {
  trace: TraceData;
}

export default function AdminQualityDetail({ trace: t }: Props) {
  return (
    <div className="mt-2 mb-4 bg-gray-800 rounded-lg p-4 text-xs space-y-3">
      <div className="text-gray-400">トレースID: {t.trace_id || "-"}</div>

      <div>
        <div className="text-gray-400 mb-1">質問</div>
        <div className="text-gray-200">{t.what?.question || "(不明)"}</div>
      </div>

      {t.pipeline?.steps && t.pipeline.steps.length > 0 && (
        <div>
          <div className="text-gray-400 mb-1">パイプラインステップ</div>
          <div className="space-y-1">
            {t.pipeline.steps.map((s, si) => (
              <div key={si} className="flex items-center gap-2">
                <span className={s.status === "ok" ? "text-green-400" : "text-red-400"}>
                  {s.status === "ok" ? "✅" : "❌"}
                </span>
                <span className="text-gray-300 w-28">{s.step}</span>
                <span className="text-blue-400 font-mono w-12 text-right">{s.seconds}s</span>
                <span className="text-gray-500 truncate">{s.detail}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="flex gap-6">
        <div>
          <div className="text-gray-400 mb-1">エージェント</div>
          <div className="text-gray-200">{t.agent?.selected_agent || "-"} ({t.agent?.agent_model || "-"})</div>
        </div>
        <div>
          <div className="text-gray-400 mb-1">エンジン</div>
          <div className="text-gray-200">{t.agent?.engine || "-"}</div>
        </div>
        <div>
          <div className="text-gray-400 mb-1">チャート</div>
          <div className="text-gray-200">{t.what?.charts?.join(", ") || "なし"}</div>
        </div>
      </div>

      {t.what?.sources_referenced && t.what.sources_referenced.length > 0 && (
        <div>
          <div className="text-gray-400 mb-1">参照データソース</div>
          <div className="text-gray-200">{t.what.sources_referenced.join(", ")}</div>
        </div>
      )}

      {t.error && (
        <div className="bg-red-900/20 rounded p-2">
          <div className="text-red-400 mb-1">エラー（ステップ: {t.error.step}）</div>
          <div className="text-red-300">{t.error.type}: {t.error.message}</div>
        </div>
      )}
    </div>
  );
}
