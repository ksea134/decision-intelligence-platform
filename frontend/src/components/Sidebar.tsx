"use client";

import { useEffect, useState } from "react";
import { Company, UserInfo, ModelsResponse, AgentInfo, CatalogHealth, fetchCompanies, fetchMe, fetchModels, fetchAgents, fetchCatalogHealth, switchModel, API_BASE, IS_LOCAL } from "@/lib/api";

interface SidebarProps {
  selectedCompany: Company | null;
  onSelectCompany: (company: Company) => void;
  onGcpConfigChange: (projectId: string, gcsBucket: string) => void;
  collapsed: boolean;
  onToggle: () => void;
}

export default function Sidebar({ selectedCompany, onSelectCompany, onGcpConfigChange, collapsed, onToggle }: SidebarProps) {
  const [companies, setCompanies] = useState<Company[]>([]);
  const [projectId, setProjectId] = useState("decision-support-ai");
  const [gcsBucket, setGcsBucket] = useState("dsa-knowledge-base");
  const [user, setUser] = useState<UserInfo | null>(null);
  const [devOpen, setDevOpen] = useState(false);
  const [models, setModels] = useState<ModelsResponse | null>(null);
  const [agents, setAgents] = useState<AgentInfo[]>([]);
  const [catalogHealth, setCatalogHealth] = useState<CatalogHealth | null>(null);

  useEffect(() => {
    fetchCompanies().then(setCompanies);
    fetchMe().then(setUser);
    fetchModels().then(setModels);
    fetchAgents().then(setAgents);
    fetchCatalogHealth().then(setCatalogHealth);
  }, []);

  const handleModelSwitch = async (role: string, modelId: string) => {
    await switchModel(role, modelId);
    const updated = await fetchModels();
    setModels(updated);
  };

  const ROLE_LABELS: Record<string, string> = {
    router: "ルーター",
    fast: "高速回答",
    deep: "深い分析",
    supplement: "補足フェーズ",
  };

  return (
    <>
      {/* 折り畳みボタン（常に表示） */}
      <button
        onClick={onToggle}
        className="fixed top-3 left-3 z-50 bg-gray-800 text-gray-300 hover:text-white
                   rounded-lg p-2 hover:bg-gray-700 transition-colors"
        title={collapsed ? "サイドバーを開く" : "サイドバーを閉じる"}
      >
        {collapsed ? "☰" : "✕"}
      </button>

      {/* サイドバー本体: 折り畳み時は完全に非表示 */}
      {!collapsed && (
      <aside className="w-72 bg-gray-900 border-r border-gray-700 p-4 pt-12 flex flex-col h-screen overflow-y-auto">

        <h1 className="text-lg font-bold text-white mb-1">DIP</h1>
        <p className="text-xs text-gray-400 mb-4">Decision Intelligence Platform</p>

        {/* ユーザー情報 */}
        {user && (
          <>
            <div className="flex items-center gap-2 mb-1">
              <span className="text-sm">👤</span>
              <span className="text-sm text-white truncate">{user.name}</span>
            </div>
            <span className="text-xs text-gray-500 mb-4">権限: {user.role}</span>
          </>
        )}

        <div className="h-px bg-gray-700 mb-4" />

        {/* 企業選択 */}
        <label className="text-xs text-gray-400 mb-1">企業を選択</label>
        <select
          className="bg-gray-800 text-white text-sm rounded px-3 py-2 mb-4 border border-gray-600 focus:border-[#FF462D] focus:outline-none"
          value={selectedCompany?.folder_name || ""}
          onChange={(e) => {
            const c = companies.find((c) => c.folder_name === e.target.value);
            if (c) onSelectCompany(c);
          }}
        >
          <option value="">-- 選択してください --</option>
          {companies.map((c) => (
            <option key={c.folder_name} value={c.folder_name}>
              {c.display_name}
            </option>
          ))}
        </select>

        {/* 開発者情報 — ローカル環境のみ表示 */}
        {IS_LOCAL && (
          <>
            <div className="h-px bg-gray-700 mb-3" />
            <button
              onClick={() => setDevOpen(!devOpen)}
              className="text-xs text-gray-500 hover:text-gray-300 flex items-center gap-1 mb-2 transition-colors"
            >
              <span>{devOpen ? "▼" : "▶"}</span>
              <span>開発者情報</span>
            </button>
            {devOpen && (
              <div className="space-y-2 mb-4">
                <a
                  href="/admin"
                  target="_blank"
                  className="text-xs text-white hover:text-[#FF462D] bg-gray-800 hover:bg-gray-700 px-3 py-1.5 rounded block text-center transition-colors mb-2"
                >
                  DIP管理画面を開く
                </a>
                <div className="flex items-center gap-2">
                  <span className="text-xs text-gray-500">環境:</span>
                  <span className="text-xs text-green-400 font-bold">LOCAL</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-xs text-gray-500">画面:</span>
                  <span className="text-xs text-gray-400 truncate">http://localhost:3000</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-xs text-gray-500">API:</span>
                  <span className="text-xs text-gray-400 truncate">{API_BASE}</span>
                </div>
                <label className="text-xs text-gray-500">Project ID</label>
                <input
                  type="text"
                  value={projectId}
                  onChange={(e) => { setProjectId(e.target.value); onGcpConfigChange(e.target.value, gcsBucket); }}
                  placeholder="GCP Project ID"
                  className="bg-gray-800 text-white text-xs rounded px-2 py-1.5 w-full border border-gray-600 focus:border-[#FF462D] focus:outline-none"
                />
                <label className="text-xs text-gray-500">GCS Bucket</label>
                <input
                  type="text"
                  value={gcsBucket}
                  onChange={(e) => { setGcsBucket(e.target.value); onGcpConfigChange(projectId, e.target.value); }}
                  placeholder="GCS Bucket Name"
                  className="bg-gray-800 text-white text-xs rounded px-2 py-1.5 w-full border border-gray-600 focus:border-[#FF462D] focus:outline-none"
                />
                {/* GCPサービス一覧 */}
                {user?.gcp_services && (
                  <div className="mt-2">
                    <div className="text-xs text-gray-500 mb-1">GCPサービス</div>
                    <div className="space-y-0.5">
                      {user.gcp_services.filter(s => s.status === "active").map((s, i) => (
                        <div key={i} className="flex items-center gap-1.5 text-xs">
                          <span className="text-green-400">●</span>
                          <span className="text-gray-300">{s.name}</span>
                          <span className="text-gray-600 text-[10px]">{s.purpose}</span>
                        </div>
                      ))}
                      {user.gcp_services.filter(s => s.status === "planned").map((s, i) => (
                        <div key={`p${i}`} className="flex items-center gap-1.5 text-xs">
                          <span className="text-gray-600">○</span>
                          <span className="text-gray-500">{s.name}</span>
                          <span className="text-gray-600 text-[10px]">{s.purpose}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
                {/* エージェント一覧 */}
                {agents.length > 0 && (
                  <div className="mt-2">
                    <div className="text-xs text-gray-500 mb-1">エージェントAI</div>
                    <div className="space-y-0.5">
                      {agents.map((a, i) => (
                        <div key={i} className="flex items-center gap-1.5 text-xs">
                          <span className="text-[#4CDD84]">●</span>
                          <span className="text-gray-300">{a.display_name}</span>
                          <span className="text-gray-600 text-[10px]">{a.current_model}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
                {/* データカタログ */}
                {catalogHealth && (
                  <div className="mt-2">
                    <div className="text-xs text-gray-500 mb-1">データカタログ</div>
                    <div className="text-xs text-gray-400">
                      テーブル: {catalogHealth.total}件（説明あり: {catalogHealth.with_description}）
                    </div>
                    {catalogHealth.without_description > 0 && (
                      <div className="text-xs text-yellow-400 mt-0.5">
                        ⚠ 説明未設定: {catalogHealth.without_description}件
                      </div>
                    )}
                  </div>
                )}
                {/* モデル設定 */}
                {models && (
                  <div className="mt-2">
                    <div className="text-xs text-gray-500 mb-1">モデル設定</div>
                    <div className="space-y-1.5">
                      {Object.entries(models.current).map(([role, modelId]) => (
                        <div key={role}>
                          <div className="text-[10px] text-gray-500">{ROLE_LABELS[role] || role}</div>
                          <select
                            value={modelId}
                            onChange={(e) => handleModelSwitch(role, e.target.value)}
                            className="bg-gray-800 text-white text-[10px] rounded px-1.5 py-1 w-full border border-gray-600 focus:border-[#FF462D] focus:outline-none"
                          >
                            {models.available.map((m) => (
                              <option key={m.id} value={m.id}>{m.name}</option>
                            ))}
                          </select>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </>
        )}

        {/* バージョン */}
        <div className="mt-auto flex items-center gap-2 text-sm text-gray-500">
          <span>powered by</span>
          <img src="/Kyndryl_logo.png" alt="Kyndryl" className="h-5 inline" />
          <span className="opacity-50">|</span>
          <span>v5.13.0</span>
        </div>
      </aside>
      )}
    </>
  );
}
