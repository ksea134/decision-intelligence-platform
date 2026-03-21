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

## 3. ハイブリッドエンジン構成（v5.6.0現在）

### V1エンジンとADKエンジンの使い分け

| 入力方法 | 使用エンジン | 特徴 | Claudeモデル |
|---------|------------|------|-------------|
| **スマートカードクリック** | V1エンジン | 高速（Gemini API 1回）。プロンプト・データソース確定済み | ✅ 利用可能 |
| **チャット入力** | ADKエンジン | サブエージェント振り分け（質問の種類に応じた専門回答） | ⬜ 未対応（Vertex AI Model Garden有効化で対応予定） |

### V1エンジン（`orchestration/reasoning_engine.py`）

- 2フェーズ固定構造: データ取得（非ストリーミング）→ 回答生成（ストリーミング）
- LLMクライアント抽象化層（`orchestration/llm_client.py`）経由でGemini/Claude自動切替
- モデル設定: `config/app_config.py` の `MODELS.fast`
- 安定性: 高（Gemini API呼び出し回数が固定、予測可能）

### ADKエンジン（`orchestration/adk/runner.py`）

- Google ADK（Agent Development Kit）ベース
- ルートエージェント → サブエージェント自動振り分け
- モデル設定: `MODELS.router`（ルーター）、`MODELS.deep`（分析系）、`MODELS.fast`（汎用）
- ADKはGemini専用。Claude利用にはVertex AI Model Garden経由が必要（後日対応）

### 補足フェーズ（`orchestration/reasoning_engine_v2.py`）

- 思考ロジック・インフォグラフィック・深掘り質問を生成
- LLMクライアント抽象化層経由でGemini/Claude自動切替
- モデル設定: `MODELS.supplement`

### モデル設定の一元管理

全エンジンのモデル設定は `config/app_config.py` の `MODELS` で一元管理:

| ロール | 用途 | デフォルト | 変更方法 |
|--------|------|-----------|---------|
| `router` | ADKルーター（質問分類） | gemini-2.5-flash | サイドバー or API |
| `fast` | V1エンジン（スマートカード）、ADK汎用 | gemini-2.5-flash | サイドバー or API |
| `deep` | ADK分析系エージェント | gemini-2.5-pro | サイドバー or API |
| `supplement` | 補足フェーズ | gemini-2.5-flash | サイドバー or API |

サイドバーの開発者情報からリアルタイムで切り替え可能（再起動不要）。

### 利用可能モデル一覧（v5.6.0現在）

| モデルID | 表示名 | プロバイダ | 速度 | コスト | ADK対応 |
|---------|--------|-----------|------|--------|---------|
| gemini-2.5-flash | Gemini 2.5 Flash | Google | 高速 | 低 | ✅ |
| gemini-2.5-pro | Gemini 2.5 Pro | Google | 標準 | 中 | ✅ |
| claude-opus-4-6 | Claude Opus 4.6 | Anthropic | 低速 | 高 | ⬜ 後日対応 |
| claude-sonnet-4-6 | Claude Sonnet 4.6 | Anthropic | 標準 | 中 | ⬜ 後日対応 |
| claude-haiku-4-5 | Claude Haiku 4.5 | Anthropic | 高速 | 低 | ⬜ 後日対応 |

ClaudeモデルはV1エンジン+補足フェーズで利用可能。ADK対応にはVertex AI Model GardenでのClaude有効化（法人申請）が必要。定義場所: `config/app_config.py` の `ModelConfig.AVAILABLE_MODELS`

## 4. エージェント構成（ADKエンジン）

| エージェント | 分類トリガー | 専門フレームワーク | モデル |
|------------|------------|------------------|--------|
| 要因分析 | 「なぜ」「原因」「理由」「要因」 | 5 Whys + 寄与度分析 | MODELS.deep |
| 比較 | 「比較」「違い」「vs」「どちらが」 | 比較表 + 強み弱み構造 | MODELS.deep |
| 予測 | 「予測」「今後」「見通し」「どうなる」 | 3シナリオ（楽観/基本/悲観） | MODELS.deep |
| 汎用 | 上記以外 | 標準プロンプト | MODELS.fast |

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
