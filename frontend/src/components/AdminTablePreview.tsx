"use client";

import { useEffect, useState } from "react";
import { API_BASE, Company, fetchCompanies } from "@/lib/api";

interface ColumnInfo {
  name: string;
  type: string;
  description: string;
}

interface TableInfo {
  table_id: string;
  dataset: string;
  columns: ColumnInfo[];
}

interface GcsFile {
  name: string;
  size: number;
  updated: string;
  file_type: string;
}

type Source = "bq" | "gcs";
type Tab = "preview" | "columns";

export default function AdminTablePreview() {
  const [companies, setCompanies] = useState<Company[]>([]);
  const [selectedCompany, setSelectedCompany] = useState("");
  const [source, setSource] = useState<Source>("bq");

  // BQ state
  const [bqTables, setBqTables] = useState<TableInfo[]>([]);
  const [selectedTable, setSelectedTable] = useState<string>("");

  // GCS state
  const [gcsFiles, setGcsFiles] = useState<GcsFile[]>([]);
  const [selectedFile, setSelectedFile] = useState<string>("");

  // Data state
  const [columns, setColumns] = useState<string[]>([]);
  const [data, setData] = useState<string[][]>([]);
  const [rowCount, setRowCount] = useState(0);
  const [totalRows, setTotalRows] = useState<number | null>(null);
  const [columnDefs, setColumnDefs] = useState<ColumnInfo[]>([]);
  const [fileType, setFileType] = useState<string>("text");
  const [downloadUrl, setDownloadUrl] = useState<string>("");
  const [previewFilename, setPreviewFilename] = useState<string>("");
  const [previewSize, setPreviewSize] = useState<number>(0);
  const [tab, setTab] = useState<Tab>("preview");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // 企業一覧を取得
  useEffect(() => {
    fetchCompanies().then((list) => {
      setCompanies(list);
      if (list.length > 0) setSelectedCompany(list[0].folder_name);
    });
  }, []);

  // 企業 or ソース変更時にテーブル/ファイル一覧を取得
  useEffect(() => {
    if (!selectedCompany) return;
    setSelectedTable("");
    setSelectedFile("");
    setColumns([]);
    setData([]);
    setColumnDefs([]);
    setError("");

    if (source === "bq") {
      setLoading(true);
      fetch(`${API_BASE}/api/admin/table-preview/bq-tables?dataset=${encodeURIComponent(selectedCompany)}`)
        .then((r) => r.json())
        .then((d) => {
          setBqTables(d.tables || []);
          if (d.error) setError(d.error);
          setLoading(false);
        })
        .catch(() => setLoading(false));
    } else {
      setLoading(true);
      fetch(`${API_BASE}/api/admin/table-preview/gcs-files?prefix=${encodeURIComponent(selectedCompany + "/")}`)
        .then((r) => r.json())
        .then((d) => {
          setGcsFiles(d.files || []);
          if (d.error) setError(d.error);
          setLoading(false);
        })
        .catch(() => setLoading(false));
    }
  }, [selectedCompany, source]);

  // BQテーブル選択時にデータ取得
  const loadBqData = (tableId: string) => {
    setSelectedTable(tableId);
    setSelectedFile("");
    setTab("preview");
    setError("");
    setFileType("text");
    setDownloadUrl("");
    const tableInfo = bqTables.find((t) => t.table_id === tableId);
    setColumnDefs(tableInfo?.columns || []);

    setLoading(true);
    fetch(`${API_BASE}/api/admin/table-preview/bq-data?dataset=${encodeURIComponent(selectedCompany)}&table=${encodeURIComponent(tableId)}&limit=100`)
      .then((r) => r.json())
      .then((d) => {
        setColumns(d.columns || []);
        setData(d.data || []);
        setRowCount(d.row_count || 0);
        setTotalRows(null);
        if (d.error) setError(d.error);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  };

  // GCSファイル選択時にデータ取得
  const loadGcsData = (filename: string) => {
    setSelectedFile(filename);
    setSelectedTable("");
    setTab("preview");
    setError("");
    setColumnDefs([]);
    setFileType("text");
    setDownloadUrl("");

    setLoading(true);
    fetch(`${API_BASE}/api/admin/table-preview/gcs-data?filename=${encodeURIComponent(filename)}&limit=100`)
      .then((r) => r.json())
      .then((d) => {
        const ft = d.file_type || "text";
        setFileType(ft);
        setColumns(d.columns || []);
        setData(d.data || []);
        setRowCount(d.row_count || 0);
        setTotalRows(d.total_rows || null);
        if (d.download_url) setDownloadUrl(d.download_url);
        if (d.filename) setPreviewFilename(d.filename);
        if (d.size) setPreviewSize(d.size);
        if (d.error) setError(d.error);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  };

  const formatSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
  };

  return (
    <div className="flex gap-4 h-[calc(100vh-200px)]">
      {/* サイドバー */}
      <div className="w-64 flex-shrink-0 flex flex-col gap-3">
        {/* 企業選択 */}
        <div>
          <label className="text-xs text-gray-400 block mb-1">企業</label>
          <select
            value={selectedCompany}
            onChange={(e) => setSelectedCompany(e.target.value)}
            className="bg-gray-800 text-white text-xs rounded px-2 py-2 border border-gray-700 w-full"
          >
            {companies.map((c) => (
              <option key={c.folder_name} value={c.folder_name}>{c.display_name}</option>
            ))}
          </select>
        </div>

        {/* ソース切替 */}
        <div className="flex gap-1">
          <button
            onClick={() => setSource("bq")}
            className={`flex-1 text-xs px-3 py-1.5 rounded transition-colors ${
              source === "bq" ? "bg-[#FF462D] text-white" : "bg-gray-800 text-gray-400 hover:text-white"
            }`}
          >
            BigQuery
          </button>
          <button
            onClick={() => setSource("gcs")}
            className={`flex-1 text-xs px-3 py-1.5 rounded transition-colors ${
              source === "gcs" ? "bg-[#FF462D] text-white" : "bg-gray-800 text-gray-400 hover:text-white"
            }`}
          >
            Cloud Storage
          </button>
        </div>

        {/* テーブル/ファイル一覧 */}
        <div className="flex-1 overflow-y-auto border border-gray-800 rounded">
          {source === "bq" ? (
            bqTables.length === 0 ? (
              <div className="text-xs text-gray-500 p-3">
                {loading ? "読み込み中..." : "テーブルがありません"}
              </div>
            ) : (
              bqTables.map((t) => (
                <button
                  key={t.table_id}
                  onClick={() => loadBqData(t.table_id)}
                  className={`w-full text-left px-3 py-2 text-xs transition-colors border-b border-gray-800 ${
                    selectedTable === t.table_id
                      ? "bg-gray-700 text-white"
                      : "text-gray-300 hover:bg-gray-800"
                  }`}
                >
                  <div className="font-mono">{t.table_id}</div>
                  <div className="text-[10px] text-gray-500">{t.columns.length} columns</div>
                </button>
              ))
            )
          ) : (
            gcsFiles.length === 0 ? (
              <div className="text-xs text-gray-500 p-3">
                {loading ? "読み込み中..." : "ファイルがありません"}
              </div>
            ) : (
              gcsFiles.map((f) => (
                <button
                  key={f.name}
                  onClick={() => loadGcsData(f.name)}
                  className={`w-full text-left px-3 py-2 text-xs transition-colors border-b border-gray-800 ${
                    selectedFile === f.name
                      ? "bg-gray-700 text-white"
                      : "text-gray-300 hover:bg-gray-800"
                  }`}
                >
                  <div className="font-mono truncate flex items-center gap-1">
                    <span className="text-[10px] opacity-60">
                      {f.file_type === "image" ? "IMG" : f.file_type === "pdf" ? "PDF" : f.file_type === "binary" ? "BIN" : "TXT"}
                    </span>
                    {f.name.split("/").pop()}
                  </div>
                  <div className="text-[10px] text-gray-500">{formatSize(f.size)}</div>
                </button>
              ))
            )
          )}
        </div>
      </div>

      {/* メインエリア */}
      <div className="flex-1 flex flex-col min-w-0">
        {!selectedTable && !selectedFile ? (
          <div className="flex-1 flex items-center justify-center text-gray-500 text-sm">
            左のリストからテーブルまたはファイルを選択してください
          </div>
        ) : (
          <>
            {/* ヘッダー */}
            <div className="flex items-center justify-between mb-2">
              <div>
                <span className="text-sm font-bold text-white font-mono">
                  {selectedTable || selectedFile?.split("/").pop()}
                </span>
                <span className="text-xs text-gray-400 ml-2">
                  {rowCount}行表示{totalRows ? ` / 全${totalRows}行` : ""}
                </span>
              </div>
              {/* タブ切替（BQのみカラム定義タブ） */}
              {source === "bq" && columnDefs.length > 0 && (
                <div className="flex gap-1">
                  <button
                    onClick={() => setTab("preview")}
                    className={`text-xs px-3 py-1 rounded ${
                      tab === "preview" ? "bg-gray-700 text-white" : "text-gray-400 hover:text-white"
                    }`}
                  >
                    データプレビュー
                  </button>
                  <button
                    onClick={() => setTab("columns")}
                    className={`text-xs px-3 py-1 rounded ${
                      tab === "columns" ? "bg-gray-700 text-white" : "text-gray-400 hover:text-white"
                    }`}
                  >
                    カラム定義
                  </button>
                </div>
              )}
            </div>

            {error && (
              <div className="text-xs text-red-400 mb-2">{error}</div>
            )}

            {loading ? (
              <div className="flex-1 flex items-center justify-center text-gray-400 text-sm">
                読み込み中...
              </div>
            ) : tab === "columns" && columnDefs.length > 0 ? (
              /* カラム定義 */
              <div className="flex-1 overflow-auto">
                <table className="w-full text-xs">
                  <thead>
                    <tr className="border-b border-gray-700 text-left text-gray-400">
                      <th className="py-2 px-3 w-48">カラム名</th>
                      <th className="py-2 px-3 w-28">型</th>
                      <th className="py-2 px-3">説明</th>
                    </tr>
                  </thead>
                  <tbody>
                    {columnDefs.map((col) => (
                      <tr key={col.name} className="border-b border-gray-800">
                        <td className="py-2 px-3 font-mono text-white">{col.name}</td>
                        <td className="py-2 px-3 text-gray-400">{col.type}</td>
                        <td className="py-2 px-3 text-gray-300">{col.description || "—"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : fileType === "image" && downloadUrl ? (
              /* 画像プレビュー */
              <div className="flex-1 flex flex-col items-center justify-center gap-4">
                <img
                  src={`${API_BASE}${downloadUrl}`}
                  alt={previewFilename}
                  className="max-w-full max-h-[60vh] object-contain rounded border border-gray-700"
                />
                <div className="text-xs text-gray-400">
                  {previewFilename} ({formatSize(previewSize)})
                </div>
              </div>
            ) : fileType === "pdf" && downloadUrl ? (
              /* PDFプレビュー */
              <div className="flex-1 flex flex-col gap-2">
                <iframe
                  src={`${API_BASE}${downloadUrl}`}
                  className="flex-1 w-full rounded border border-gray-700 bg-white"
                  title={previewFilename}
                />
                <div className="text-xs text-gray-400 flex items-center gap-3">
                  <span>{previewFilename} ({formatSize(previewSize)})</span>
                  <a
                    href={`${API_BASE}${downloadUrl}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-blue-400 hover:text-blue-300"
                  >
                    新しいタブで開く
                  </a>
                </div>
              </div>
            ) : fileType === "binary" && downloadUrl ? (
              /* バイナリファイル（ダウンロードリンク） */
              <div className="flex-1 flex flex-col items-center justify-center gap-4">
                <div className="text-4xl text-gray-600">
                  {previewFilename.match(/\.(pptx?|docx?|xlsx?)$/i) ? "DOC" :
                   previewFilename.match(/\.(mp3|wav|ogg)$/i) ? "AUDIO" :
                   previewFilename.match(/\.(mp4|mov|avi|mkv|webm)$/i) ? "VIDEO" : "FILE"}
                </div>
                <div className="text-sm text-gray-300">{previewFilename}</div>
                <div className="text-xs text-gray-500">{formatSize(previewSize)}</div>
                <a
                  href={`${API_BASE}${downloadUrl}`}
                  download={previewFilename}
                  className="text-xs bg-gray-700 hover:bg-gray-600 text-white px-4 py-2 rounded transition-colors"
                >
                  ダウンロード
                </a>
              </div>
            ) : (
              /* テーブル形式データプレビュー */
              <div className="flex-1 overflow-auto">
                {columns.length > 0 ? (
                  <table className="w-full text-xs border-collapse">
                    <thead className="sticky top-0 bg-[#0A0E14]">
                      <tr className="border-b border-gray-700">
                        <th className="py-2 px-2 text-left text-gray-500 w-10">#</th>
                        {columns.map((col) => (
                          <th key={col} className="py-2 px-2 text-left text-gray-400 font-mono whitespace-nowrap">
                            {col}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {data.map((row, ri) => (
                        <tr key={ri} className="border-b border-gray-800/50 hover:bg-gray-900/50">
                          <td className="py-1.5 px-2 text-gray-600">{ri + 1}</td>
                          {row.map((cell, ci) => {
                            const isPlainText = columns.length === 1 && columns[0] === "内容";
                            return (
                              <td
                                key={ci}
                                className={`py-1.5 px-2 text-gray-200 ${
                                  isPlainText
                                    ? "whitespace-pre-wrap break-all"
                                    : "whitespace-nowrap max-w-[300px] truncate"
                                }`}
                                title={isPlainText ? undefined : cell}
                              >
                                {cell || "—"}
                              </td>
                            );
                          })}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                ) : (
                  <div className="text-gray-500 text-sm p-4">データがありません</div>
                )}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
