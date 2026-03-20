"use client";

import { useState } from "react";
import Sidebar from "@/components/Sidebar";
import Chat from "@/components/Chat";
import { Company } from "@/lib/api";

export default function Home() {
  const [selectedCompany, setSelectedCompany] = useState<Company | null>(null);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  return (
    <div className="flex h-screen">
      <Sidebar
        selectedCompany={selectedCompany}
        onSelectCompany={setSelectedCompany}
        collapsed={sidebarCollapsed}
        onToggle={() => setSidebarCollapsed(!sidebarCollapsed)}
      />
      <main className="flex-1 bg-gray-950">
        {selectedCompany ? (
          <Chat company={selectedCompany} />
        ) : (
          <div className="flex items-center justify-center h-full">
            <div className="text-center">
              <h2 className="text-2xl font-bold text-white mb-2">意思決定支援AI</h2>
              <p className="text-gray-400">左側のメニューから企業を選択してください</p>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
