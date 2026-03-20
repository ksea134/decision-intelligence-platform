"use client";

import { useEffect, useState } from "react";
import { Company, fetchCompanies } from "@/lib/api";

interface SidebarProps {
  selectedCompany: Company | null;
  onSelectCompany: (company: Company) => void;
}

export default function Sidebar({ selectedCompany, onSelectCompany }: SidebarProps) {
  const [companies, setCompanies] = useState<Company[]>([]);

  useEffect(() => {
    fetchCompanies().then(setCompanies);
  }, []);

  return (
    <aside className="w-72 bg-gray-900 border-r border-gray-700 p-4 flex flex-col h-screen">
      <h1 className="text-lg font-bold text-white mb-1">DIP</h1>
      <p className="text-xs text-gray-400 mb-4">Decision Intelligence Platform</p>

      {/* 企業選択 */}
      <label className="text-xs text-gray-400 mb-1">企業を選択</label>
      <select
        className="bg-gray-800 text-white text-sm rounded px-3 py-2 mb-6 border border-gray-600 focus:border-blue-500 focus:outline-none"
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

      {/* バージョン */}
      <div className="mt-auto text-xs text-gray-500">
        powered by Kyndryl | v5.0.0
      </div>
    </aside>
  );
}
