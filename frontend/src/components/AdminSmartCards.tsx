"use client";

import React, { useEffect, useState, useRef } from "react";
import { API_BASE } from "@/lib/api";

interface SmartCardAdmin {
  id: string;
  icon: string;
  icon_type: string;
  title: string;
  data_source: string;
  visible: boolean;
  engine: string;
  timing: string;
  period: string;
  domain: string;
  prompt_template: string;
  company_code: string;
  company_name: string;
  _isNew?: boolean;
  _oldId?: string;
}

interface CompanyInfo {
  folder_name: string;
  display_name: string;
}

const DATA_SOURCE_OPTIONS = [
  { value: "all", label: "全データ" },
  { value: "structured", label: "構造化" },
  { value: "unstructured", label: "非構造化" },
];

const ICON_TYPE_OPTIONS = [
  { value: "emoji", label: "絵文字" },
  { value: "symbol", label: "Material Symbols" },
  { value: "image", label: "画像" },
];

const TIMING_OPTIONS = ["", "随時", "日次", "週次", "月次", "四半期次"];
const PERIOD_OPTIONS = ["", "24時間", "昨日", "7日間", "今週", "1ヶ月", "3ヶ月", "今月"];
const DOMAIN_OPTIONS = ["", "工場", "品質", "安全", "監査", "経営", "在庫"];

/** コード入力欄 — 独自stateで再描画を防ぐ */
function CodeInput({ value, onChange }: { value: string; onChange: (v: string) => void }) {
  const [local, setLocal] = useState(value);
  useEffect(() => { setLocal(value); }, [value]);
  return (
    <input
      type="text"
      value={local}
      onChange={(e) => setLocal(e.target.value)}
      onBlur={() => {
        const cleaned = local.replace(/[^a-zA-Z0-9_]/g, "");
        setLocal(cleaned);
        onChange(cleaned);
      }}
      className="bg-gray-800 text-white text-xs rounded px-2 py-1.5 border border-gray-700 focus:border-[#FF462D] focus:outline-none w-full font-mono"
      placeholder="card_code"
    />
  );
}

export default function AdminSmartCards() {
  const [cards, setCards] = useState<SmartCardAdmin[]>([]);
  const [companies, setCompanies] = useState<CompanyInfo[]>([]);
  const [deleted, setDeleted] = useState<{ company_code: string; id: string }[]>([]);
  const [filter, setFilter] = useState<string>("all");
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(true);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [uploadTarget, setUploadTarget] = useState<number | null>(null);
  const [dirty, setDirty] = useState(false);
  const [initialJson, setInitialJson] = useState("");
  const [expandedPrompt, setExpandedPrompt] = useState<number | null>(null);

  // ページ離脱時の確認ダイアログ
  useEffect(() => {
    const handler = (e: BeforeUnloadEvent) => {
      if (dirty) {
        e.preventDefault();
      }
    };
    window.addEventListener("beforeunload", handler);
    return () => window.removeEventListener("beforeunload", handler);
  }, [dirty]);


  useEffect(() => {
    fetch(`${API_BASE}/api/admin/smart-cards`)
      .then((r) => r.json())
      .then((data) => {
        const loaded = (data.cards || []).map((c: SmartCardAdmin) => ({ ...c, _oldId: c.id }));
        setCards(loaded);
        setInitialJson(JSON.stringify(loaded.map(({ _isNew, _oldId, ...rest }: any) => rest)));
        setCompanies(data.companies || []);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  const filteredCards = filter === "all" ? cards : cards.filter((c) => c.company_code === filter);

  const updateCard = (index: number, field: keyof SmartCardAdmin, value: any) => {
    setDirty(true);
    setCards((prev) => {
      const realIndex = filter === "all" ? index : prev.indexOf(filteredCards[index]);
      const next = [...prev];
      next[realIndex] = { ...next[realIndex], [field]: value };
      return next;
    });
  };

  const addCard = () => {
    setDirty(true);
    const companyCode = filter !== "all" ? filter : companies[0]?.folder_name || "";
    const companyName = companies.find((c) => c.folder_name === companyCode)?.display_name || "";
    setCards((prev) => [
      ...prev,
      {
        id: "",
        icon: "📋",
        icon_type: "emoji",
        title: "",
        data_source: "all",
        visible: true,
        engine: "v1",
        timing: "",
        period: "",
        domain: "",
        prompt_template: "",
        company_code: companyCode,
        company_name: companyName,
        _isNew: true,
      },
    ]);
  };

  const deleteCard = (index: number) => {
    setDirty(true);
    const realIndex = filter === "all" ? index : cards.indexOf(filteredCards[index]);
    const card = cards[realIndex];
    if (!card._isNew && card.id) {
      setDeleted((prev) => [...prev, { company_code: card.company_code, id: card.id }]);
    }
    setCards((prev) => prev.filter((_, i) => i !== realIndex));
  };

  const saveOneCard = async (index: number) => {
    const realIndex = filter === "all" ? index : cards.indexOf(filteredCards[index]);
    const card = cards[realIndex];
    if (!card.id.trim() || !card.title.trim()) {
      setMessage("コードとタイトルは必須です");
      setTimeout(() => setMessage(""), 3000);
      return;
    }
    setSaving(true);
    try {
      // 同じ企業の全カードをまとめて送る（CSV全体を書き換えるため）
      const companyCards = cards.filter((c) => c.company_code === card.company_code);
      const res = await fetch(`${API_BASE}/api/admin/smart-cards/save`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          cards: companyCards.map((c) => ({
            company_code: c.company_code,
            id: c.id,
            old_id: c._oldId && c._oldId !== c.id ? c._oldId : "",
            icon: c.icon,
            icon_type: c.icon_type,
            title: c.title,
            data_source: c.data_source,
            visible: c.visible,
            engine: c.engine,
            timing: c.timing,
            period: c.period,
            domain: c.domain,
            prompt_template: c.prompt_template,
          })),
          deleted: deleted.filter((d) => d.company_code === card.company_code),
        }),
      });
      const result = await res.json();
      setMessage(`「${card.title}」を保存しました`);
      // この企業の削除済みをクリア、_oldIdを更新
      setDeleted((prev) => prev.filter((d) => d.company_code !== card.company_code));
      setCards((prev) =>
        prev.map((c) =>
          c.company_code === card.company_code ? { ...c, _isNew: false, _oldId: c.id } : c
        )
      );
    } catch {
      setMessage("保存に失敗しました");
    }
    setSaving(false);
    setTimeout(() => setMessage(""), 3000);
  };

  const handleSave = async () => {
    // バリデーション
    for (const card of cards) {
      if (!card.id.trim()) {
        setMessage("コードが空のカードがあります");
        setTimeout(() => setMessage(""), 3000);
        return;
      }
      if (!card.title.trim()) {
        setMessage("タイトルが空のカードがあります");
        setTimeout(() => setMessage(""), 3000);
        return;
      }
    }

    setSaving(true);
    try {
      const res = await fetch(`${API_BASE}/api/admin/smart-cards/save`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          cards: cards.map((c) => ({
            company_code: c.company_code,
            id: c.id,
            old_id: c._oldId && c._oldId !== c.id ? c._oldId : "",
            icon: c.icon,
            icon_type: c.icon_type,
            title: c.title,
            data_source: c.data_source,
            visible: c.visible,
            engine: c.engine,
            timing: c.timing,
            period: c.period,
            domain: c.domain,
            prompt_template: c.prompt_template,
          })),
          deleted,
        }),
      });
      const result = await res.json();
      setMessage(result.message || "保存しました");
      setDeleted([]);
      // _isNewフラグをクリア、_oldIdを現在のidに更新、dirty解除
      setCards((prev) => prev.map((c) => ({ ...c, _isNew: false, _oldId: c.id })));
      setDirty(false);
    } catch {
      setMessage("保存に失敗しました");
    }
    setSaving(false);
    setTimeout(() => setMessage(""), 3000);
  };

  const handleIconUpload = async (index: number, file: File) => {
    const realIndex = filter === "all" ? index : cards.indexOf(filteredCards[index]);
    const card = cards[realIndex];
    const formData = new FormData();
    formData.append("company", card.company_code);
    formData.append("file", file);
    try {
      const res = await fetch(`${API_BASE}/api/admin/smart-cards/upload-icon`, {
        method: "POST",
        body: formData,
      });
      const result = await res.json();
      if (result.path) {
        updateCard(index, "icon", result.path);
        updateCard(index, "icon_type", "image");
      }
    } catch {
      setMessage("アイコンのアップロードに失敗しました");
      setTimeout(() => setMessage(""), 3000);
    }
  };

  const isCustomDataSource = (ds: string) => {
    return ds.startsWith("bq:") || ds.startsWith("gcs:");
  };

  if (loading) {
    return <div className="text-gray-400 text-sm">読み込み中...</div>;
  }

  return (
    <div>
      {/* ヘッダー: フィルタ + アクション */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex gap-2 flex-wrap">
          <button
            onClick={() => setFilter("all")}
            className={`text-xs px-3 py-1.5 rounded-full transition-colors ${
              filter === "all"
                ? "bg-[#FF462D] text-white"
                : "bg-gray-800 text-gray-400 hover:text-white"
            }`}
          >
            全企業 ({cards.length})
          </button>
          {companies.map((c) => {
            const count = cards.filter((card) => card.company_code === c.folder_name).length;
            return (
              <button
                key={c.folder_name}
                onClick={() => setFilter(c.folder_name)}
                className={`text-xs px-3 py-1.5 rounded-full transition-colors ${
                  filter === c.folder_name
                    ? "bg-[#FF462D] text-white"
                    : "bg-gray-800 text-gray-400 hover:text-white"
                }`}
              >
                {c.display_name} ({count})
              </button>
            );
          })}
        </div>
        <div className="flex gap-2 items-center">
          {message && (
            <span className="text-xs text-green-400">{message}</span>
          )}
          <button
            onClick={addCard}
            className="text-xs bg-gray-700 hover:bg-gray-600 text-white px-3 py-1.5 rounded transition-colors"
          >
            + カード追加
          </button>
          <button
            onClick={handleSave}
            disabled={saving}
            className="text-xs bg-[#FF462D] hover:bg-[#FF462D]/80 text-white px-4 py-1.5 rounded transition-colors disabled:opacity-50"
          >
            {saving ? "保存中..." : "全て保存"}
          </button>
        </div>
      </div>

      {/* 非表示アイコンアップロード用input */}
      <input
        ref={fileInputRef}
        type="file"
        accept="image/*"
        className="hidden"
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file && uploadTarget !== null) {
            handleIconUpload(uploadTarget, file);
          }
          e.target.value = "";
        }}
      />

      {/* テーブル */}
      <div className="overflow-x-auto">
        <table className="w-full text-xs min-w-[1000px]">
          <thead>
            <tr className="border-b border-gray-700 text-left text-xs text-gray-400">
              <th className="py-2 px-1 w-24">企業</th>
              <th className="py-2 px-1 w-20">アイコン</th>
              <th className="py-2 px-1 w-28">タイトル</th>
              <th className="py-2 px-1 w-20">コード</th>
              <th className="py-2 px-1 w-20">ソース</th>
              <th className="py-2 px-1 w-16">エンジン</th>
              <th className="py-2 px-1 w-16">タイミング</th>
              <th className="py-2 px-1 w-16">期間</th>
              <th className="py-2 px-1 w-16">ドメイン</th>
              <th className="py-2 px-1 w-14">プロンプト</th>
              <th className="py-2 px-1 w-10 text-center">表示</th>
              <th className="py-2 px-1 w-12 text-center">操作</th>
            </tr>
          </thead>
          <tbody>
            {filteredCards.map((card, i) => (
              <React.Fragment key={`${card.company_code}-${card.id}-${i}`}>
              <tr className="border-b border-gray-800 hover:bg-gray-900/50 align-top">
                {/* 企業 */}
                <td className="py-2 px-2">
                  {card._isNew ? (
                    <select
                      value={card.company_code}
                      onChange={(e) => {
                        const code = e.target.value;
                        const name = companies.find((c) => c.folder_name === code)?.display_name || "";
                        updateCard(i, "company_code", code);
                        updateCard(i, "company_name", name);
                      }}
                      className="bg-gray-800 text-white text-xs rounded px-2 py-1 border border-gray-600 w-full"
                    >
                      {companies.map((c) => (
                        <option key={c.folder_name} value={c.folder_name}>{c.display_name}</option>
                      ))}
                    </select>
                  ) : (
                    <span className="text-xs text-gray-300">{card.company_name}</span>
                  )}
                </td>

                {/* アイコン */}
                <td className="py-2 px-2">
                  <div className="flex items-center gap-1">
                    <select
                      value={card.icon_type}
                      onChange={(e) => updateCard(i, "icon_type", e.target.value)}
                      className="bg-gray-800 text-white text-xs rounded px-1 py-1 border border-gray-700 w-16"
                    >
                      {ICON_TYPE_OPTIONS.map((o) => (
                        <option key={o.value} value={o.value}>{o.label}</option>
                      ))}
                    </select>
                    {card.icon_type === "image" ? (
                      <button
                        onClick={() => {
                          setUploadTarget(i);
                          fileInputRef.current?.click();
                        }}
                        className="text-xs bg-gray-700 hover:bg-gray-600 rounded px-2 py-1 truncate max-w-[60px]"
                        title={card.icon || "アップロード"}
                      >
                        {card.icon ? "変更" : "選択"}
                      </button>
                    ) : (
                      <input
                        type="text"
                        value={card.icon}
                        onChange={(e) => updateCard(i, "icon", e.target.value)}
                        className="bg-gray-800 text-white text-xs rounded px-2 py-1 border border-gray-700 w-12 text-center"
                        placeholder={card.icon_type === "emoji" ? "📋" : "search"}
                      />
                    )}
                  </div>
                </td>

                {/* タイトル */}
                <td className="py-2 px-2">
                  <input
                    type="text"
                    value={card.title}
                    onChange={(e) => updateCard(i, "title", e.target.value)}
                    className="bg-gray-800 text-white text-xs rounded px-2 py-1.5 border border-gray-700 focus:border-[#FF462D] focus:outline-none w-full"
                    placeholder="カードタイトル"
                  />
                </td>

                {/* コード */}
                <td className="py-2 px-2">
                  <CodeInput value={card.id} onChange={(v) => updateCard(i, "id", v)} />
                </td>

                {/* データソース */}
                <td className="py-2 px-2">
                  {isCustomDataSource(card.data_source) ? (
                    <input
                      type="text"
                      value={card.data_source}
                      onChange={(e) => updateCard(i, "data_source", e.target.value)}
                      className="bg-gray-800 text-white text-xs rounded px-2 py-1.5 border border-gray-700 focus:border-[#FF462D] focus:outline-none w-full font-mono"
                    />
                  ) : (
                    <select
                      value={card.data_source}
                      onChange={(e) => updateCard(i, "data_source", e.target.value)}
                      className="bg-gray-800 text-white text-xs rounded px-2 py-1.5 border border-gray-700 w-full"
                    >
                      {DATA_SOURCE_OPTIONS.map((o) => (
                        <option key={o.value} value={o.value}>{o.label}</option>
                      ))}
                      <option value="bq:">bq:（手入力）</option>
                      <option value="gcs:">gcs:（手入力）</option>
                    </select>
                  )}
                </td>

                {/* エンジン */}
                <td className="py-2 px-2">
                  <select
                    value={card.engine}
                    onChange={(e) => updateCard(i, "engine", e.target.value)}
                    className={`bg-gray-800 text-xs rounded px-2 py-1.5 border border-gray-700 w-full ${
                      card.engine === "adk" ? "text-orange-400" : "text-white"
                    }`}
                  >
                    <option value="v1">V1 高速</option>
                    <option value="adk">ADK 精度</option>
                  </select>
                </td>

                {/* タイミング */}
                <td className="py-2 px-2">
                  <select
                    value={card.timing}
                    onChange={(e) => updateCard(i, "timing", e.target.value)}
                    className="bg-gray-800 text-white text-xs rounded px-2 py-1.5 border border-gray-700 w-full"
                  >
                    {TIMING_OPTIONS.map((o) => (
                      <option key={o} value={o}>{o || "—"}</option>
                    ))}
                  </select>
                </td>

                {/* 取得期間 */}
                <td className="py-2 px-2">
                  <select
                    value={card.period}
                    onChange={(e) => updateCard(i, "period", e.target.value)}
                    className="bg-gray-800 text-white text-xs rounded px-2 py-1.5 border border-gray-700 w-full"
                  >
                    {PERIOD_OPTIONS.map((o) => (
                      <option key={o} value={o}>{o || "—"}</option>
                    ))}
                  </select>
                </td>

                {/* 業務ドメイン */}
                <td className="py-2 px-2">
                  <select
                    value={card.domain}
                    onChange={(e) => updateCard(i, "domain", e.target.value)}
                    className="bg-gray-800 text-white text-xs rounded px-2 py-1.5 border border-gray-700 w-full"
                  >
                    {DOMAIN_OPTIONS.map((o) => (
                      <option key={o} value={o}>{o || "—"}</option>
                    ))}
                  </select>
                </td>

                {/* プロンプト */}
                <td className="py-2 px-1 text-center">
                  <button
                    onClick={() => setExpandedPrompt(expandedPrompt === i ? null : i)}
                    className={`text-xs px-3 py-1.5 rounded w-full transition-colors ${
                      expandedPrompt === i
                        ? "bg-[#FF462D] text-white"
                        : card.prompt_template
                          ? "bg-gray-700 text-gray-300 hover:bg-gray-600"
                          : "bg-gray-800 text-gray-500 hover:bg-gray-700"
                    }`}
                  >
                    {expandedPrompt === i ? "閉じる" : card.prompt_template ? "編集" : "追加"}
                  </button>
                </td>

                {/* 表示トグル */}
                <td className="py-2 px-2 text-center">
                  <button
                    onClick={() => updateCard(i, "visible", !card.visible)}
                    className="relative inline-flex items-center h-6 w-11 rounded-full transition-colors"
                    style={{ backgroundColor: card.visible ? "#22c55e" : "#4b5563" }}
                    title={card.visible ? "表示中 — クリックで非表示" : "非表示 — クリックで表示"}
                  >
                    <span
                      className={`inline-block h-4 w-4 rounded-full bg-white shadow transform transition-transform ${
                        card.visible ? "translate-x-6" : "translate-x-1"
                      }`}
                    />
                  </button>
                </td>

                {/* 操作 */}
                <td className="py-2 px-2 text-center">
                  <div className="flex flex-col gap-1 items-center">
                    <button
                      onClick={() => saveOneCard(i)}
                      disabled={saving}
                      className="text-xs text-gray-400 hover:text-green-400 transition-colors disabled:opacity-50"
                      title="このカードだけ保存"
                    >
                      保存
                    </button>
                    <button
                      onClick={() => {
                        if (confirm(`「${card.title || card.id}」を削除しますか？`)) {
                          deleteCard(i);
                        }
                      }}
                      className="text-xs text-gray-500 hover:text-red-400 transition-colors"
                      title="削除"
                    >
                      削除
                    </button>
                  </div>
                </td>
              </tr>
              {expandedPrompt === i && (
                <tr className="border-b border-gray-700 bg-gray-900/80">
                  <td colSpan={12} className="py-3 px-4">
                    <div className="text-[10px] text-gray-400 mb-1">プロンプト — {card.title}</div>
                    <textarea
                      value={card.prompt_template}
                      onChange={(e) => updateCard(i, "prompt_template", e.target.value)}
                      rows={Math.max(4, Math.min(12, (card.prompt_template.match(/\n/g) || []).length + 2))}
                      className="bg-gray-800 text-white text-xs rounded px-3 py-2 border border-gray-700 focus:border-[#FF462D] focus:outline-none w-full resize-y font-mono leading-relaxed"
                      placeholder="プロンプトテンプレートを入力..."
                    />
                  </td>
                </tr>
              )}
              </React.Fragment>
            ))}
          </tbody>
        </table>
      </div>

      {filteredCards.length === 0 && (
        <div className="text-center text-gray-500 text-sm py-8">
          カードがありません。「+ カード追加」で追加してください。
        </div>
      )}
    </div>
  );
}
