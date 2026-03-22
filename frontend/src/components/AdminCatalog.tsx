"use client";

import { useEffect, useState } from "react";
import { API_BASE } from "@/lib/api";

interface TableInfo {
  table: string;
  dataset: string;
  has_description: boolean;
  description: string;
  linked_resource: string;
  columns_total: number;
  columns_with_desc: number;
}

interface ColumnInfo {
  name: string;
  type: string;
  description: string;
}

interface TableDetail {
  table: string;
  description: string;
  columns: ColumnInfo[];
}

export default function AdminCatalog() {
  const [tables, setTables] = useState<TableInfo[]>([]);
  const [total, setTotal] = useState(0);
  const [withDesc, setWithDesc] = useState(0);
  const [withoutDesc, setWithoutDesc] = useState(0);
  const [expandedTable, setExpandedTable] = useState<string | null>(null);
  const [detail, setDetail] = useState<TableDetail | null>(null);
  const [editDesc, setEditDesc] = useState("");
  const [columnEdits, setColumnEdits] = useState<Record<string, string>>({});
  const [saving, setSaving] = useState(false);
  const [inlineMessage, setInlineMessage] = useState("");
  const [savedColumn, setSavedColumn] = useState("");

  useEffect(() => {
    fetch(`${API_BASE}/api/catalog/health`)
      .then((r) => r.json())
      .then((data) => {
        setTables(data.tables || []);
        setTotal(data.total || 0);
        setWithDesc(data.with_description || 0);
        setWithoutDesc(data.without_description || 0);
      });
  }, []);

  const handleExpand = async (t: TableInfo) => {
    if (expandedTable === t.table) {
      setExpandedTable(null);
      setDetail(null);
      return;
    }
    setExpandedTable(t.table);
    setInlineMessage("");
    const [dataset, table] = t.table.split(".");
    const res = await fetch(`${API_BASE}/api/catalog/table-detail?dataset=${dataset}&table=${table}`);
    const d = await res.json();
    setDetail(d);
    setEditDesc(d.description || "");
    const edits: Record<string, string> = {};
    (d.columns || []).forEach((c: ColumnInfo) => { edits[c.name] = c.description || ""; });
    setColumnEdits(edits);
  };

  const handleSaveTableDesc = async () => {
    if (!expandedTable) return;
    setSaving(true);
    const [dataset, table] = expandedTable.split(".");
    const res = await fetch(`${API_BASE}/api/catalog/update`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ dataset, table, description: editDesc }),
    });
    const result = await res.json();
    setInlineMessage(result.message || "保存しました");
    setSavedColumn("");
    setSaving(false);
    setTimeout(() => setInlineMessage(""), 3000);
    // 一覧を更新
    setTables((prev) =>
      prev.map((t) => t.table === expandedTable ? { ...t, description: editDesc, has_description: !!editDesc } : t)
    );
    setWithDesc((prev) => prev + (editDesc ? 1 : 0));
    setWithoutDesc((prev) => prev - (editDesc ? 1 : 0));
  };

  const handleSaveColumnDesc = async (column: string) => {
    if (!expandedTable) return;
    setSaving(true);
    const [dataset, table] = expandedTable.split(".");
    const res = await fetch(`${API_BASE}/api/catalog/update-column`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ dataset, table, column, description: columnEdits[column] || "" }),
    });
    const result = await res.json();
    setInlineMessage(result.message || "保存しました");
    setSavedColumn(column);
    setSaving(false);
    setTimeout(() => { setInlineMessage(""); setSavedColumn(""); }, 3000);
  };

  // データセットごとにグループ化
  const datasets = [...new Set(tables.map((t) => t.dataset))].sort();

  return (
    <div>
      {/* サマリー */}
      <div className="flex gap-6 mb-6">
        <div className="bg-gray-800 rounded-lg px-4 py-3">
          <div className="text-2xl font-bold text-white">{total}</div>
          <div className="text-xs text-gray-400">テーブル総数</div>
        </div>
        <div className="bg-gray-800 rounded-lg px-4 py-3">
          <div className="text-2xl font-bold text-green-400">{withDesc}</div>
          <div className="text-xs text-gray-400">説明あり</div>
        </div>
        <div className="bg-gray-800 rounded-lg px-4 py-3">
          <div className="text-2xl font-bold text-yellow-400">{withoutDesc}</div>
          <div className="text-xs text-gray-400">説明なし</div>
        </div>
      </div>

      {/* データセット別テーブル一覧 */}
      {datasets.map((ds) => (
        <div key={ds} className="mb-4">
          <div className="text-sm font-bold text-gray-300 mb-2 border-b border-gray-700 pb-1">{ds}</div>
          <div className="space-y-1">
            {tables.filter((t) => t.dataset === ds).map((t) => (
              <div key={t.table}>
                <button
                  onClick={() => handleExpand(t)}
                  className="w-full text-left flex items-center gap-2 px-3 py-2 rounded hover:bg-gray-800 transition-colors"
                >
                  <span className={t.has_description ? "text-green-400" : "text-yellow-400"} title="テーブル説明">
                    {t.has_description ? "✅" : "⚠"}
                  </span>
                  <span className={t.columns_total > 0 && t.columns_with_desc === t.columns_total ? "text-green-400" : "text-yellow-400"} title={`カラム説明: ${t.columns_with_desc}/${t.columns_total}`}>
                    {t.columns_total > 0 && t.columns_with_desc === t.columns_total ? "✅" : "⚠"}
                  </span>
                  <span className="text-sm text-gray-200">{t.table.split(".")[1]}</span>
                  {t.description && (
                    <span className="text-xs text-gray-500 truncate ml-2">{t.description}</span>
                  )}
                  <span className="text-[10px] text-gray-600 ml-1">
                    ({t.columns_with_desc}/{t.columns_total})
                  </span>
                  <span className="ml-auto text-xs text-gray-600">
                    {expandedTable === t.table ? "▼" : "▶"}
                  </span>
                </button>

                {/* 展開時: テーブル説明 + カラム一覧 */}
                {expandedTable === t.table && detail && (
                  <div className="ml-8 mt-2 mb-4 space-y-3">
                    {/* テーブル説明 */}
                    <div>
                      <label className="text-xs text-gray-400">テーブル説明</label>
                      <div className="flex gap-2 mt-1">
                        <input
                          type="text"
                          value={editDesc}
                          onChange={(e) => setEditDesc(e.target.value)}
                          placeholder="例: 生産実績データ。日別・ライン別の計画数量と実績数量"
                          className="flex-1 bg-gray-800 text-white text-sm rounded px-3 py-2
                                     border border-gray-600 focus:border-[#FF462D] focus:outline-none"
                        />
                        <button
                          onClick={handleSaveTableDesc}
                          disabled={saving}
                          className={`text-sm text-white px-4 py-2 rounded disabled:opacity-50 transition-colors ${
                            editDesc ? "bg-gray-700 hover:bg-gray-600" : "bg-[#FF462D] hover:bg-[#FF462D]/80"
                          }`}
                        >
                          保存
                        </button>
                      </div>
                      {inlineMessage && !savedColumn && (
                        <div className="text-xs text-green-400 mt-1">{inlineMessage}</div>
                      )}
                    </div>

                    {/* カラム一覧 */}
                    <div>
                      <label className="text-xs text-gray-400">カラム</label>
                      <div className="mt-1 space-y-1">
                        {detail.columns.map((col) => (
                          <div key={col.name}>
                            <div className="flex items-center gap-2">
                              <span className="text-xs text-gray-500 w-32 truncate" title={col.name}>
                                {col.name}
                              </span>
                              <span className="text-[10px] text-gray-600 w-16">{col.type}</span>
                              <input
                                type="text"
                                value={columnEdits[col.name] || ""}
                                onChange={(e) => setColumnEdits({ ...columnEdits, [col.name]: e.target.value })}
                                placeholder="カラムの説明"
                                className="flex-1 bg-gray-800 text-white text-xs rounded px-2 py-1.5
                                           border border-gray-700 focus:border-[#FF462D] focus:outline-none"
                              />
                              <button
                                onClick={() => handleSaveColumnDesc(col.name)}
                                disabled={saving}
                                className={`text-xs px-2 py-1.5 rounded disabled:opacity-50 transition-colors ${
                                  columnEdits[col.name]
                                    ? "text-gray-400 hover:text-white bg-gray-700 hover:bg-gray-600"
                                    : "text-white bg-[#FF462D] hover:bg-[#FF462D]/80"
                                }`}
                              >
                                保存
                              </button>
                            </div>
                            {savedColumn === col.name && inlineMessage && (
                              <div className="text-[10px] text-green-400 ml-32 mt-0.5">{inlineMessage}</div>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
