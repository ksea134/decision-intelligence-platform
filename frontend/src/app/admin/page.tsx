"use client";

import { useState } from "react";
import AdminCatalog from "@/components/AdminCatalog";

const TABS = [
  { id: "catalog", label: "データカタログ", ready: true },
  { id: "agents", label: "エージェント", ready: false },
  { id: "feedback", label: "フィードバック", ready: false },
  { id: "permissions", label: "権限", ready: false },
];

export default function AdminPage() {
  const [activeTab, setActiveTab] = useState("catalog");

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

      {/* コンテンツ */}
      <div className="px-6 py-6 max-w-6xl mx-auto">
        {activeTab === "catalog" && <AdminCatalog />}
        {activeTab === "agents" && (
          <div className="text-gray-500 text-sm">エージェント管理は段階2で実装予定です。</div>
        )}
        {activeTab === "feedback" && (
          <div className="text-gray-500 text-sm">フィードバック分析は段階3で実装予定です。</div>
        )}
        {activeTab === "permissions" && (
          <div className="text-gray-500 text-sm">権限管理は段階4で実装予定です。</div>
        )}
      </div>
    </div>
  );
}
