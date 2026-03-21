"use client";

import { useState, useEffect } from "react";
import Sidebar from "@/components/Sidebar";
import Chat from "@/components/Chat";
import { Company } from "@/lib/api";

export default function Home() {
  const [selectedCompany, setSelectedCompany] = useState<Company | null>(null);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [projectId, setProjectId] = useState("decision-support-ai");
  const [gcsBucket, setGcsBucket] = useState("dsa-knowledge-base");
  const [isMobile, setIsMobile] = useState(false);

  useEffect(() => {
    const check = () => setIsMobile(window.innerWidth < 768);
    check();
    window.addEventListener("resize", check);
    return () => window.removeEventListener("resize", check);
  }, []);

  // モバイルではサイドバーをデフォルトで閉じる
  useEffect(() => {
    if (isMobile) setSidebarCollapsed(true);
  }, [isMobile]);

  const handleSelectCompany = (company: Company) => {
    setSelectedCompany(company);
    if (isMobile) setSidebarCollapsed(true);
  };

  return (
    <div className="flex h-screen relative">
      {/* モバイル: オーバーレイ背景 */}
      {isMobile && !sidebarCollapsed && (
        <div
          className="fixed inset-0 bg-black/60 z-40"
          onClick={() => setSidebarCollapsed(true)}
        />
      )}

      <div className={isMobile && !sidebarCollapsed ? "fixed inset-y-0 left-0 z-50" : ""}>
        <Sidebar
          selectedCompany={selectedCompany}
          onSelectCompany={handleSelectCompany}
          onGcpConfigChange={(pid, bucket) => { setProjectId(pid); setGcsBucket(bucket); }}
          collapsed={sidebarCollapsed}
          onToggle={() => setSidebarCollapsed(!sidebarCollapsed)}
        />
      </div>

      <main className="flex-1 bg-[#0A0E14] min-w-0">
        {selectedCompany ? (
          <Chat company={selectedCompany} projectId={projectId} gcsBucket={gcsBucket} />
        ) : (
          <div className="flex items-center justify-center h-full px-4">
            <div className="text-center">
              <h2 className="text-xl md:text-2xl font-bold text-white mb-2">意思決定支援AI</h2>
              <p className="text-sm md:text-base text-gray-400">
                {isMobile ? "☰ メニューから企業を選択" : "左側のメニューから企業を選択してください"}
              </p>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
