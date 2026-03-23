"use client";

import { useState, useEffect } from "react";
import AdminCatalog from "@/components/AdminCatalog";
import AdminAgents from "@/components/AdminAgents";
import AdminFeedback from "@/components/AdminFeedback";
import AdminQuality from "@/components/AdminQuality";
import AdminSmartCards from "@/components/AdminSmartCards";
import AdminTablePreview from "@/components/AdminTablePreview";

const TABS = [
  { id: "quality", label: "AI品質管理", ready: true },
  { id: "feedback", label: "利用者FB", ready: true },
  { id: "agents", label: "AIエージェント", ready: true },
  { id: "table_preview", label: "テーブルプレビュー", ready: true },
  { id: "catalog", label: "データカタログ", ready: true },
  { id: "smart_cards", label: "スマートカード", ready: true },
  { id: "permissions", label: "権限", ready: false },
];

export default function AdminPage() {
  const [activeTab, setActiveTab] = useState("quality");
  const [mountedTabs, setMountedTabs] = useState<Set<string>>(new Set(["quality"]));

  // 一度開いたタブを記録（以降アンマウントしない）
  useEffect(() => {
    setMountedTabs((prev) => {
      if (prev.has(activeTab)) return prev;
      return new Set(prev).add(activeTab);
    });
  }, [activeTab]);

  useEffect(() => {
    const link = document.querySelector("link[rel='icon']") as HTMLLinkElement;
    if (link) link.href = "/favicon-admin.svg";
    return () => { if (link) link.href = "/favicon.svg"; };
  }, []);

  return (
    <div className="min-h-screen bg-[#0A0E14] text-white">
      {/* ヘッダー */}
      <div className="border-b border-gray-800 px-6 py-4">
        <div className="flex items-center justify-between max-w-6xl mx-auto">
          <div>
            <h1 className="text-lg font-bold">DIP 管理画面</h1>
            <p className="text-xs text-gray-400">Decision Intelligence Platform — Admin</p>
          </div>
          <a
            href="/"
            className="text-sm text-gray-400 hover:text-white bg-gray-800 hover:bg-gray-700 px-4 py-2 rounded-lg transition-colors"
          >
            DIPに戻る
          </a>
        </div>
      </div>

      {/* タブ */}
      <div className="border-b border-gray-800 px-6">
        <div className="flex gap-1 max-w-6xl mx-auto">
          {TABS.map((tab) => (
            <button
              key={tab.id}
              onClick={() => tab.ready && setActiveTab(tab.id)}
              className={`px-4 py-3 text-sm transition-colors border-b-2 ${
                activeTab === tab.id
                  ? "border-[#FF462D] text-white"
                  : tab.ready
                    ? "border-transparent text-gray-400 hover:text-gray-200"
                    : "border-transparent text-gray-600 cursor-default"
              }`}
            >
              {tab.label}
              {!tab.ready && <span className="text-[10px] text-gray-600 ml-1">（準備中）</span>}
            </button>
          ))}
        </div>
      </div>

      {/* コンテンツ — 一度開いたタブは常駐、表示/非表示で切替（遅延マウント） */}
      <div className="px-6 py-6 max-w-6xl mx-auto">
        {mountedTabs.has("quality") && <div className={activeTab === "quality" ? "" : "hidden"}><AdminQuality /></div>}
        {mountedTabs.has("feedback") && <div className={activeTab === "feedback" ? "" : "hidden"}><AdminFeedback /></div>}
        {mountedTabs.has("agents") && <div className={activeTab === "agents" ? "" : "hidden"}><AdminAgents /></div>}
        {mountedTabs.has("table_preview") && <div className={activeTab === "table_preview" ? "" : "hidden"}><AdminTablePreview /></div>}
        {mountedTabs.has("catalog") && <div className={activeTab === "catalog" ? "" : "hidden"}><AdminCatalog /></div>}
        {mountedTabs.has("smart_cards") && <div className={activeTab === "smart_cards" ? "" : "hidden"}><AdminSmartCards /></div>}
        {mountedTabs.has("permissions") && <div className={activeTab === "permissions" ? "" : "hidden"}>
          <div className="text-gray-500 text-sm">権限管理は段階4で実装予定です。</div>
        </div>}
      </div>
    </div>
  );
}
