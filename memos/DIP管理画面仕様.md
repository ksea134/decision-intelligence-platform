# DIP管理画面仕様

> 作成日: 2026-03-22
> 更新日: 2026-03-22

---

## 1. 概要

DIPの設定・データ管理を一元的に行う管理画面。Next.jsアプリ内の `/admin` ページとして実装し、IAP認証を共有する。

### 背景

| 管理対象 | 現在の方法 | 問題 |
|---------|-----------|------|
| テーブル説明・カラム説明 | BigQueryコンソールで1つずつ編集 | 面倒。テーブルが増えると運用に耐えない |
| エージェント設定 | agents.jsonを手動編集 | 非エンジニアが触れない |
| モデル設定 | サイドバーの開発者情報 | 一時的（再起動でリセット） |
| フィードバック分析 | Looker Studioで別画面 | DIPの外に出る必要がある |

### DIPの価値向上

管理画面の導入により、DIPは「AIチャット」から**「データ資産管理プラットフォーム」**に格上げされる。お客様のIT部門がGCPコンソールの操作を覚えずにDIPを管理できる。

---

## 2. 管理画面の構成（4タブ）

| タブ | 機能 | 対応する層別仕様 | 実装段階 |
|------|------|----------------|---------|
| **データカタログ** | テーブル・カラム説明の閲覧・編集、未設定警告 | Storage層 + Governance層 | 段階1（今回） |
| **エージェント管理** | エージェント追加・プロンプト変更・モデル設定 | Orchestration層 | 段階2 |
| **フィードバック分析** | 👍👎一覧、企業別分析、コメント検索 | AI Ops層 | 段階3 |
| **ユーザー・権限管理** | ユーザー別テーブルアクセス権限の設定 | Governance層 + Security&Governance層 | 段階4 |

---

## 3. 段階1: データカタログ管理

### 機能

| # | 機能 | 対応API |
|---|------|--------|
| 1 | テーブル一覧表示（説明あり/なし、カラム情報） | `/api/catalog/health` 拡張 |
| 2 | テーブル説明の編集（その場で入力→BigQueryに保存） | `/api/catalog/update`（新規） |
| 3 | カラム説明の編集 | `/api/catalog/update-column`（新規） |
| 4 | 未設定テーブルの警告ハイライト | フロントエンドのみ |

### 画面イメージ

```
┌─────────────────────────────────────────────────────────┐
│ DIP管理画面                                              │
│ [データカタログ] [エージェント] [フィードバック] [権限]     │
├─────────────────────────────────────────────────────────┤
│                                                         │
│ テーブル一覧（32件 / 説明あり: 4件 / ⚠未設定: 28件）      │
│                                                         │
│ ┌─ demo_factory02 ──────────────────────────────────┐   │
│ │ ⚠ incident_records                                │   │
│ │   説明: [                              ] [保存]    │   │
│ │   カラム: date, area, incident_type, severity...   │   │
│ │                                                    │   │
│ │ ⚠ production_results                              │   │
│ │   説明: [                              ] [保存]    │   │
│ │   カラム: date, line, shift, plan_qty...           │   │
│ └────────────────────────────────────────────────────┘   │
│                                                         │
│ ┌─ demo_factory ────────────────────────────────────┐   │
│ │ ✅ mes_a3_line_operation                           │   │
│ │   説明: A-3ライン稼働実績（製造実行システム）       │   │
│ │   カラム: measured_at, line_name, status...         │   │
│ └────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

### 修正対象ファイル

| CP | 内容 | ファイル |
|----|------|---------|
| CP1 | 管理画面のページ | `frontend/src/app/admin/page.tsx`（新規） |
| CP2 | データカタログ管理コンポーネント | `frontend/src/components/AdminCatalog.tsx`（新規） |
| CP3 | テーブル説明更新API | `backend/api/catalog.py`（拡張） |

### API費用

| API | 費用 | 備考 |
|-----|------|------|
| Data Catalog `search_catalog()` | **無料** | メタデータ読み取り |
| Data Catalog `lookup_entry()` | **無料** | メタデータ読み取り |
| BigQuery テーブル/カラム説明更新 | **無料** | メタデータ更新 |
| Dataplex データ品質ジョブ | **有料** | 段階4以降。使用時に費用確認が必要 |
| Dataplex データプロファイリング | **有料** | 段階4以降。使用時に費用確認が必要 |

管理画面を開くたびにData Catalog APIが約25〜30回呼ばれるが、全て無料。5分TTLキャッシュで2回目以降は即表示。

### 変更しないもの（厳守）
- Chat.tsx — 触らない
- Sidebar.tsx — 触らない
- reasoning_engine.py, adk/ — 触らない

---

## 4. 段階2: エージェント管理（将来）

### 機能

| # | 機能 |
|---|------|
| 1 | エージェント一覧表示（名前、モデル、トリガーキーワード） |
| 2 | プロンプト（instruction）の編集 |
| 3 | モデルの切り替え（ロール別） |
| 4 | エージェントの追加・削除 |

### データソース
- 現在: `config/agents.json`（ローカルファイル）
- 将来: Vertex AI Agent Builder API

---

## 5. 段階3: フィードバック分析（将来）

### 機能

| # | 機能 |
|---|------|
| 1 | 👍👎フィードバック一覧（時系列） |
| 2 | 企業別・エージェント別の満足度分析 |
| 3 | 👎コメント検索・フィルタ |
| 4 | 品質スコアのトレンド表示 |

### データソース
- BigQuery `dip_ops.v_feedback` ビュー
- 将来: Vertex AI Evaluation結果

---

## 6. 段階4: ユーザー・権限管理（将来）

### 機能

| # | 機能 |
|---|------|
| 1 | ユーザー一覧表示（IAP認証ユーザー） |
| 2 | ユーザー別アクセス可能テーブルの設定 |
| 3 | 権限テンプレート（部門別等） |

### データソース
- 現在: `config/data_catalog.json` の permissions セクション
- 将来: Dataplex Data Governance API

---

## 7. AI品質管理 — ログ設計（2026-03-22設計）

### 大原則

ログの目的はきれいなグラフを作ることではない。以下の4つを実現するためにある：

1. **問題の特定**: 何が起きたか即座にわかる
2. **責任分解点の明確化**: パイプラインのどのステップで、どのコンポーネントが問題を起こしたか
3. **影響範囲の把握**: 誰が、どの企業で影響を受けたか
4. **迅速な復旧**: 原因がわかれば対処できる

### パイプラインステップ定義（最大粒度）

**これはDIPのAI品質管理の根幹である。全ステップの時間・ステータス・詳細を記録する。**

| # | ステップ | 内容 | V1 | ADK | detail例 |
|---|---------|------|-----|-----|---------|
| 1 | `data_load` | BQスキーマ・GCS資料・ローカルファイルの読み込み | ✅ | ✅ | BQ: 152 chars, GCS: 11857 chars |
| 2 | `past_qa_search` | Vertex AI Searchで過去の類似Q&Aを検索 | ✅ | ✅ | 3 similar QAs found / 未接続 |
| 3 | `table_select` | Dataplexカタログ→AIエージェントで関連テーブル絞り込み | ✅ | ✅ | AI selected 5/12: incident_records, ... |
| 4 | `bq_fetch` | 選択テーブルからSELECT * でデータ取得 | ✅ | ✅ | 5 tables, 342 rows |
| 5 | `agent_route` | ルーターが質問を分類→専門エージェントに振り分け | - | ✅ | → analysis_agent |
| 6 | `llm_generate` | Gemini/Claudeによる回答生成（ストリーミング） | ✅ | ✅ | model=gemini-2.5-pro, agent=analysis_agent |

管理画面テーブルヘッダー:
```
時刻 | 企業 | ユーザー | 合計 | 読込 | 検索 | 選択 | BQ | ルート | 生成 | Agent | 状態
```

### RequestTraceレコード構造

全リクエストで以下の構造化JSONをログ出力する：

```json
{
  "trace_id": "req-abc123",
  "timestamp": "2026-03-22T15:30:00Z",
  "who": {
    "user": "koya@example.com",
    "company": "製造業デモ02",
    "source": "chat"
  },
  "what": {
    "question": "安全パトロールの指摘件数は？",
    "response_length": 2500,
    "response_status": "success",
    "charts": ["bar", "mermaid"],
    "sources_referenced": ["BQ:incident_records", "GCS:report.md"]
  },
  "pipeline": {
    "total_seconds": 15.3,
    "steps": [
      {"step": "data_load",      "seconds": 1.2, "status": "ok", "detail": "BQ: 12 tables, GCS: 5 files"},
      {"step": "past_qa_search", "seconds": 0.8, "status": "ok", "detail": "3 similar QAs found"},
      {"step": "table_select",   "seconds": 2.1, "status": "ok", "detail": "AI selected 5/12"},
      {"step": "bq_fetch",       "seconds": 3.5, "status": "ok", "detail": "5 tables, 342 rows"},
      {"step": "agent_route",    "seconds": 0.1, "status": "ok", "detail": "→ analysis_agent"},
      {"step": "llm_generate",   "seconds": 7.6, "status": "ok", "detail": "model=gemini-2.5-pro, agent=analysis_agent"}
    ]
  },
  "agent": {
    "engine": "adk",
    "router_model": "gemini-2.5-flash",
    "selected_agent": "analysis_agent",
    "agent_model": "gemini-2.5-pro",
    "agent_seconds": 7.6
  },
  "error": null
}
```

### 管理画面の表示

- サマリーカード（1行）: 総件数、平均時間、P95、エラー率、品質スコア
- フィルタ: 企業別、エンジン別、ユーザー別
- ログテーブル（中心）: 時刻、企業、ユーザー、合計、読込、選択、BQ、生成、Agent、状態
- 行クリック → 詳細パネル（質問文、各ステップ詳細、エラー情報）
- 「もっと読み込む」ボタンで50件ずつ追加（無限スクロールではなく意図的な読み込み）

### 対応できるインシデント例

| インシデント | ログから特定できること |
|------------|---------------------|
| 回答が遅い | どのステップが遅いか |
| 回答がおかしい | どのエージェント、どのテーブルを使ったか |
| 特定ユーザーだけ問題 | ユーザーフィルタで一覧 |
| 特定企業だけエラー | 企業フィルタでパターン把握 |
| 昨日から急に遅い | 時系列でステップ別時間の変化確認 |
| データが取れない | BQフェッチステップのエラー詳細確認 |

### 実装対象ファイル

| # | 内容 | ファイル |
|---|------|---------|
| 1 | RequestTraceデータクラス | `backend/ops/request_trace.py`（新規） |
| 2 | V1エンジンでステップ別計測 | `orchestration/reasoning_engine.py` |
| 3 | ADKエンジンでステップ別計測 | `orchestration/adk/runner.py` |
| 4 | chat.pyでTrace出力 | `backend/api/chat.py` |
| 5 | quality APIをTrace対応 | `backend/api/quality.py` |
| 6 | 管理画面をログテーブル中心に再設計 | `AdminQuality.tsx` |

### API費用

RequestTraceの記録はCloud Logging（stdout）経由。追加のAPI費用なし。BigQueryシンクで自動永続化（既設定済み）。

## 8. テスト計画書（AI品質管理）

| # | テスト内容 | 確認方法 |
|---|-----------|---------|
| T1 | V1エンジンでRequestTraceが記録される | test01でスマートカード→ログにJSON Trace確認 |
| T2 | ADKエンジンでRequestTraceが記録される | demo_factory02でチャット→ログにJSON Trace確認 |
| T3 | ステップ別時間が正しく記録される | 各ステップのsecondsが0以上 |
| T4 | エージェント情報が記録される | agent.selected_agent, agent.agent_model確認 |
| T5 | エラー時にerrorフィールドが記録される | 意図的にエラーを発生させる |
| T6 | 管理画面にログテーブルが表示される | /admin → AI品質管理タブ |
| T7 | フィルタ（企業・エンジン・ユーザー）が動作する | 各フィルタで絞り込み |
| T8 | 行クリックで詳細パネルが開く | テーブル行をクリック |
| T9 | 「もっと読み込む」で追加データが表示される | ボタンクリック |
| T10 | 既存のチャット機能に影響がない | 回帰テスト |

### 合格基準
10項目中10項目PASS

## 9. テスト計画書（段階1 — データカタログ）

| # | テスト内容 | 確認方法 |
|---|-----------|---------|
| T1 | `/admin` ページが表示される | ブラウザ確認 |
| T2 | テーブル一覧が表示される（全データセット） | 画面確認 |
| T3 | 説明未設定テーブルが警告ハイライトされる | 画面確認 |
| T4 | テーブル説明を編集して保存できる | 入力→保存→BigQuery確認 |
| T5 | カラム説明を編集して保存できる | 入力→保存→BigQuery確認 |
| T6 | 既存のチャット機能に影響がない | `/` で質問→回答正常 |
| T7 | モバイル（375px）で管理画面が崩れない | DevTools確認 |

### 合格基準
7項目中7項目PASS

---

## 8. MECE分析との対応

| 管理画面タブ | 対応する層別仕様 | 現在のステータス |
|-------------|----------------|----------------|
| データカタログ | Storage層、Governance層 | 段階1実装予定 |
| エージェント管理 | Orchestration層 | 段階2（将来） |
| フィードバック分析 | AI Ops層 | 段階3（将来） |
| ユーザー・権限管理 | Governance層、Security&Governance層 | 段階4（将来） |

管理画面は層別仕様の4つの層を横断するUI統合レイヤーとして位置づけられる。
