"use client";

import { useEffect, useState } from "react";
import { API_BASE } from "@/lib/api";

interface AgentConfig {
  name: string;
  display_name: string;
  model_role: string;
  triggers: string[];
  instruction: string;
}

export default function AdminAgents() {
  const [agents, setAgents] = useState<AgentConfig[]>([]);
  const [router, setRouter] = useState<AgentConfig | null>(null);
  const [expandedAgent, setExpandedAgent] = useState<string | null>(null);
  const [editInstruction, setEditInstruction] = useState("");
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");
  const [savedAgent, setSavedAgent] = useState("");

  useEffect(() => {
    fetch(`${API_BASE}/api/agents/detail`)
      .then((r) => r.json())
      .then((data) => {
        setAgents(data.agents || []);
        if (data.router) setRouter(data.router);
      });
  }, []);

  const handleExpand = (agent: AgentConfig) => {
    if (expandedAgent === agent.name) {
      setExpandedAgent(null);
      return;
    }
    setExpandedAgent(agent.name);
    setEditInstruction(agent.instruction || "");
    setMessage("");
  };

  const handleSave = async (name: string) => {
    setSaving(true);
    const res = await fetch(`${API_BASE}/api/agents/update`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, instruction: editInstruction }),
    });
    const result = await res.json();
    setMessage(result.message || "保存しました");
    setSavedAgent(name);
    setSaving(false);
    setTimeout(() => { setMessage(""); setSavedAgent(""); }, 3000);

    // ローカル状態も更新
    if (router && router.name === name) {
      setRouter({ ...router, instruction: editInstruction });
    } else {
      setAgents((prev) =>
        prev.map((a) => a.name === name ? { ...a, instruction: editInstruction } : a)
      );
    }
  };

  const allAgents = router ? [router, ...agents] : agents;

  return (
    <div>
      <div className="text-xs text-gray-400 mb-2">
        エージェントの設定は config/agents.json に保存されます。変更後はバックエンドの再起動で反映されます。
      </div>
      <div className="text-xs text-gray-400 mb-4">
        ⚠ プロンプトの保存には数秒かかる場合があります。保存ボタン押下後、メッセージが表示されるまでお待ちください。
      </div>

      {/* ① ADKエージェント */}
      <div className="mb-2">
        <div className="text-sm font-bold text-gray-300 mb-2 border-b border-gray-700 pb-1">① ルーティング＋専門分析</div>
        <div className="text-xs text-gray-400 mb-2">質問を分類し、専門エージェントが回答を生成する（agents.json）</div>
      </div>

      <div className="space-y-2">
        {allAgents.map((agent) => (
          <div key={agent.name} className="border border-gray-800 rounded-lg">
            <button
              onClick={() => handleExpand(agent)}
              className="w-full text-left flex items-center gap-3 px-4 py-3 hover:bg-gray-800 transition-colors rounded-lg"
            >
              <span className="text-[#4CDD84]">●</span>
              <span className="text-sm font-bold text-gray-200">{agent.display_name}</span>
              <span className="text-[10px] text-gray-500">{agent.model_role}</span>
              {agent.triggers && agent.triggers.length > 0 && (
                <span className="text-[10px] text-gray-600">
                  [{agent.triggers.join(", ")}]
                </span>
              )}
              <span className="ml-auto text-xs text-gray-600">
                {expandedAgent === agent.name ? "▼" : "▶"}
              </span>
            </button>

            {expandedAgent === agent.name && (
              <div className="px-4 pb-4">
                <label className="text-xs text-gray-400">プロンプト（instruction）</label>
                <textarea
                  value={editInstruction}
                  onChange={(e) => setEditInstruction(e.target.value)}
                  rows={10}
                  className="w-full mt-1 bg-gray-800 text-white text-xs rounded px-3 py-2
                             border border-gray-700 focus:border-[#FF462D] focus:outline-none
                             resize-y font-mono"
                />
                <div className="flex items-center gap-2 mt-2">
                  <button
                    onClick={() => handleSave(agent.name)}
                    disabled={saving}
                    className="text-sm text-white bg-[#FF462D] hover:bg-[#FF462D]/80 px-4 py-2 rounded
                               disabled:opacity-50 transition-colors"
                  >
                    保存
                  </button>
                  {savedAgent === agent.name && message && (
                    <span className="text-xs text-green-400">{message}</span>
                  )}
                </div>
              </div>
            )}
          </div>
        ))}
      </div>

      {/* ② テーブル選択エージェント */}
      <div className="mt-6">
        <div className="text-sm font-bold text-gray-300 mb-2 border-b border-gray-700 pb-1">② テーブル選択</div>
        <div className="text-xs text-gray-400 mb-2">質問に関連するテーブルをDataplexカタログから絞り込む（data_catalog.py）</div>
        <div className="border border-gray-800 rounded-lg px-4 py-3">
          <div className="flex items-center gap-3">
            <span className="text-[#4CDD84]">●</span>
            <span className="text-sm font-bold text-gray-200">テーブル選択エージェント</span>
            <span className="text-[10px] text-gray-500">router（Gemini Flash）</span>
          </div>
          <div className="text-xs text-gray-500 mt-1 ml-6">
            Dataplex Data Catalog APIからテーブルのメタデータ（説明・カラム名）を取得し、質問に関連する最大5テーブルを選択。プロンプトはコード内で定義（C07例外: 最適化判断はAIに適した仕事）
          </div>
        </div>
      </div>
    </div>
  );
}
