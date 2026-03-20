"use client";

import { useEffect, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { CompanyAssets, fetchCompanyAssets } from "@/lib/api";

interface FlowStep {
  step: string;
  done: boolean;
  detail?: string;
}

interface RightColumnProps {
  folderName: string;
  projectId: string;
  gcsBucket: string;
  flowSteps: FlowStep[];
  thoughtProcess: string;
}

function SectionLabel({ label }: { label: string }) {
  return (
    <div className="flex items-center gap-2 my-3">
      <div className="flex-1 h-px bg-white/15" />
      <span className="text-xs text-gray-400 tracking-wider whitespace-nowrap">{label}</span>
      <div className="flex-1 h-px bg-white/15" />
    </div>
  );
}

function Expander({ title, defaultOpen = false, children }: { title: string; defaultOpen?: boolean; children: React.ReactNode }) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="mb-1">
      <button
        onClick={() => setOpen(!open)}
        className="w-full text-left text-sm text-gray-300 hover:text-white px-2 py-1.5 rounded hover:bg-gray-800 transition-colors flex items-center gap-1"
      >
        <span className="text-xs">{open ? "▼" : "▶"}</span>
        {title}
      </button>
      {open && <div className="px-2 pb-2 text-xs text-gray-400">{children}</div>}
    </div>
  );
}

export default function RightColumn({ folderName, projectId, gcsBucket, flowSteps, thoughtProcess }: RightColumnProps) {
  const [assets, setAssets] = useState<CompanyAssets | null>(null);

  useEffect(() => {
    if (folderName) {
      fetchCompanyAssets(folderName, projectId, gcsBucket).then(setAssets);
    }
  }, [folderName, projectId, gcsBucket]);

  if (!assets) return null;

  const statusIcon = (connected: boolean, isError: boolean) => {
    if (isError) return "🔴";
    if (connected) return "🟢";
    return "⚪";
  };

  return (
    <div className="h-full overflow-y-auto p-3 text-sm">
      {/* ナビゲーション */}
      <SectionLabel label="ナビゲーション" />
      <Expander title="はじめに">
        {assets.intro_text ? (
          <div className="right-column-md">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{assets.intro_text}</ReactMarkdown>
          </div>
        ) : (
          <p className="text-gray-500">設定なし</p>
        )}
      </Expander>

      {/* プロンプト */}
      <SectionLabel label="プロンプト" />
      <Expander title={`前提知識（${assets.knowledge_files.length}件）`}>
        {assets.knowledge_text ? (
          <div className="right-column-md">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {assets.knowledge_text.length >= 500
                ? assets.knowledge_text.substring(0, 500) + "..."
                : assets.knowledge_text}
            </ReactMarkdown>
          </div>
        ) : (
          <p className="text-gray-500">設定なし</p>
        )}
      </Expander>
      <Expander title="役割・回答方針">
        {assets.prompt_text ? (
          <div className="right-column-md">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {assets.prompt_text}
            </ReactMarkdown>
          </div>
        ) : (
          <p className="text-gray-500">設定なし</p>
        )}
      </Expander>

      {/* 処理概要 */}
      <SectionLabel label="処理概要" />
      <Expander title="AI処理フロー" defaultOpen={false}>
        {flowSteps.length > 0 ? (
          <div className="space-y-1">
            {flowSteps.map((step, i) => (
              <div key={i} className="flex items-center gap-2">
                <span>{step.done ? "✅" : "⏳"}</span>
                <span>{step.step}</span>
                {step.detail && <span className="text-gray-500 text-xs ml-1">{step.detail}</span>}
              </div>
            ))}
          </div>
        ) : (
          <p className="text-gray-500">質問を送信すると、処理フローが表示されます。</p>
        )}
      </Expander>
      <Expander title="AI思考ロジック" defaultOpen={false}>
        {thoughtProcess ? (
          <div className="right-column-md">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {thoughtProcess
                .split("\n")
                .map((line) => {
                  const trimmed = line.trim();
                  if (!trimmed || trimmed.startsWith("-") || trimmed.startsWith("*") || trimmed.startsWith("#")) return line;
                  return `- ${line}`;
                })
                .join("\n")}
            </ReactMarkdown>
          </div>
        ) : (
          <p className="text-gray-500">回答の表示から数秒後に、思考ロジックが表示されます。</p>
        )}
      </Expander>

      {/* データ取得先 */}
      <SectionLabel label="データ取得先" />
      <Expander title="データソース稼働状況" defaultOpen={false}>
        <div className="space-y-1">
          <div>{statusIcon(assets.bq.is_connected, assets.bq.is_error)} BigQuery: {assets.bq.is_connected ? `接続済み（${assets.bq.table_count}テーブル）` : "未接続"}</div>
          <div>{statusIcon(assets.gcs.is_connected, assets.gcs.is_error)} GCS: {assets.gcs.is_connected ? `接続済み（${assets.gcs.file_count}件）` : "未接続"}</div>
          <div>⚪ ローカル: 接続済み（{assets.local.structured_files.length + assets.local.unstructured_files.length}件）</div>
        </div>
      </Expander>
      <Expander title={`構造化データ（${assets.bq.is_connected ? assets.bq.table_count + "テーブル" : "--"}）`}>
        {assets.bq.is_error ? (
          <p className="text-red-400">🔴 BigQuery 接続エラー: {assets.bq.error_detail}</p>
        ) : assets.bq.tables && assets.bq.tables.length > 0 ? (
          <ul className="list-disc list-inside">
            {assets.bq.tables.map((t, i) => <li key={i}><code>{t}</code></li>)}
          </ul>
        ) : (
          <p className="text-gray-500">未接続</p>
        )}
      </Expander>
      <Expander title={`非構造化データ（${assets.gcs.is_connected ? assets.gcs.file_count + "件" : "--"}）`}>
        {assets.gcs.is_error ? (
          <p className="text-red-400">🔴 GCS 接続エラー: {assets.gcs.error_detail}</p>
        ) : assets.gcs.files.length > 0 ? (
          <ul className="list-disc list-inside">
            {assets.gcs.files.map((f, i) => <li key={i}><code>{f.trim()}</code></li>)}
          </ul>
        ) : (
          <p className="text-gray-500">（GCS資料なし）</p>
        )}
      </Expander>
      {/* ローカルファイル（BQ/GCS接続時は優先順位により抑制される） */}
      {(assets.local.structured_files.length > 0 || assets.local.unstructured_files.length > 0) && (
        <Expander title={`ローカルファイル（${assets.local.structured_files.length + assets.local.unstructured_files.length}件）`}>
          {assets.local.structured_files.length > 0 && (
            <>
              <p className="text-gray-400 mb-1">構造化:</p>
              <ul className="list-disc list-inside mb-2">
                {assets.local.structured_files.map((f, i) => <li key={i}><code>{f}</code></li>)}
              </ul>
            </>
          )}
          {assets.local.unstructured_files.length > 0 && (
            <>
              <p className="text-gray-400 mb-1">非構造化:</p>
              <ul className="list-disc list-inside">
                {assets.local.unstructured_files.map((f, i) => <li key={i}><code>{f}</code></li>)}
              </ul>
            </>
          )}
        </Expander>
      )}
    </div>
  );
}
