# DIP Orchestration層 仕様

> 作成日: 2026-03-19
> ステータス: 実装済み（v4 + ADK基盤）

---

## 1. 役割

ユーザーの質問を受け取り、データ取得・回答生成・補足情報生成までの全フローを制御する。DIPの頭脳。

## 2. 処理フロー

```
ユーザーの質問
  ↓
1. 質問理解
  ↓
2. 過去事例検索（Vertex AI Search）
  企業単位で類似Q&Aを検索 → 過去の分析結果をコンテキストに注入
  ↓
3. ルートエージェント（キーワード分類）
  質問を4分類: 要因分析 / 比較 / 予測 / 汎用
  ↓
4. 専門エージェント（intent別プロンプト切替）
  ↓
5. データ取得（BigQuery）
  全テーブル SELECT * で取得 → CSVデータをプロンプトに注入
  ↓
6. 回答生成（Gemini Flash/Pro / ストリーミング）
  過去事例 + BQデータ + GCS資料 + 専門フレームワーク → 回答
  ↓
7. 補足フェーズ
  ├── 思考ロジック生成
  ├── インフォグラフィック生成
  └── 深掘り質問生成
  ↓
8. Q&A自動保存（Vertex AI Search）
  質問・回答・企業名・エージェント分類を自動保存
```

## 3. エンジン構成

| エンジン | フラグ | 説明 |
|---------|-------|------|
| ADKエンジン | `USE_ADK_ENGINE=True` | Google ADK（Agent Development Kit）ベース。現在のデフォルト |
| V1エンジン + Router | `USE_AGENT_ROUTER=True` | 従来のReasoningEngine + RouterAgent |
| V1エンジン | 両方False | 最もシンプル。Router分類なし |

ADKが未インストールの環境（Streamlit Cloud等）では自動的にV1エンジンにフォールバック。

## 4. エージェント構成

| エージェント | 分類トリガー | 専門フレームワーク | モデル |
|------------|------------|------------------|--------|
| 要因分析 | 「なぜ」「原因」「理由」「要因」 | 5 Whys + 寄与度分析 | Gemini 2.5 Pro |
| 比較 | 「比較」「違い」「vs」「どちらが」 | 比較表 + 強み弱み構造 | Gemini 2.5 Pro |
| 予測 | 「予測」「今後」「見通し」「どうなる」 | 3シナリオ（楽観/基本/悲観） | Gemini 2.5 Pro |
| 汎用 | 上記以外 | 標準プロンプト | Gemini 2.5 Flash |

### 導入メリット

- **精度向上**: 専門エージェントが専門の指示で回答
- **質の分化**: タスク別に最適な回答形式
- **モデル使い分け**: コストと精度の最適化
- **拡張性**: 新エージェント追加が容易
- **デバッグ容易**: 問題の切り分けが容易

## 5. Vertex AI Search（長期記憶）

過去のQ&Aを企業単位で永続保存し、類似事例検索で回答精度を向上。

→ 詳細は `memos/層別仕様_Security＆Governance層.md` セクション4（データ分離設計）も参照

| 項目 | 内容 |
|------|------|
| 保存単位 | 企業名（個人に紐づかない） |
| 保存タイミング | 回答生成後に自動 |
| 検索タイミング | 質問受信直後 |
| 検索件数 | 上位3件 |
| 保存期間 | 無期限 |
| 失敗時 | チャット動作に影響しない |

**DIPの差別化ポイント:** 一般的な生成AIは会話が終わったら忘れる。DIPは使えば使うほど賢くなる。

## 6. キャッシュアーキテクチャ

| 処理 | 所要時間 | キャッシュ方式 |
|---|---|---|
| BigQueryスキーマ取得 | 3〜8秒 | `@st.cache_data`（TTL 5分） |
| GCSドキュメント取得 | 2〜5秒 | `@st.cache_data`（TTL 5分） |
| Vertex AI Search接続 | 1〜3秒 | `@st.cache_resource`（永続） |

キャッシュヒット時はほぼ0秒。Phase 5でStreamlit依存を解消予定。

| ファイル | 現在 | Phase 5移行後 |
|---|---|---|
| `infra/bigquery_service.py` | `@st.cache_data` | `lru_cache` or Redis |
| `infra/gcs_service.py` | `@st.cache_data` | `lru_cache` or Redis |
| `infra/vertex_ai_search.py` | `@st.cache_resource` | シングルトン |

## 7. v4再設計の経緯

| | v1〜v3.1 | v4 |
|--|---------|-----|
| SQLを誰が考えるか | Gemini（毎回違うSQL） | DIP（SELECT * 固定） |
| Gemini呼び出し回数 | 不定（1〜10回以上） | 1回固定 |
| データ取得の判断 | Geminiに委ねる | DIPが必ず実行 |
| ループ | あり（抜けないことがある） | なし |

### 補足・予備知識: AIの回答が毎回変わる理由

AIは確率的に言葉を選ぶため、同じ質問でも毎回少し違う回答になる。DIPでは`temperature=0.0`に設定して安定化しているが、Geminiの内部思考ステップにもランダム性があるため完全に同じにはならない。

## 8. 主要ファイル

| ファイル | 役割 |
|---------|------|
| `orchestration/reasoning_engine.py` | V1エンジン（安定版） |
| `orchestration/adk/runner.py` | ADKエンジン |
| `orchestration/adk/agent_definition.py` | ADKエージェント定義 |
| `orchestration/adk/tools.py` | ADKツール（BigQuery, Search） |
| `orchestration/agents/data_agent.py` | データ取得エージェント |
| `orchestration/agents/router_agent.py` | 意図分類ルーター |
| `orchestration/memory/session_memory.py` | セッション記憶（インメモリ） |
| `domain/prompt_builder.py` | システムプロンプト構築 |
| `domain/sql_validator.py` | SQLバリデーション |
| `domain/response_parser.py` | レスポンス解析 |
