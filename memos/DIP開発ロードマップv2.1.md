# DIP開発ロードマップ v2.1

> 作成日: 2026-03-17
> 更新日: 2026-03-20

---

## 目次

0. 全体像
1. フォルダ構成
2. Phase 0: 基盤準備・仕様策定（完了）
3. Phase 1: Agent Router（完了）
4. Phase 2: Memory Store統合（スキップ）
5. Phase 3: Vertex AI Search統合（完了）
6. Phase 4A: Agent Builder基盤（完了）
7. Phase 4B: エコシステム連携（一部完了）
8. Phase 5: エンタープライズUI移行（未着手）
9. Phase 6: Governance層実装（未着手）
10. Phase 7: Observability & FinOps（未着手）
11. Phase 8: 高度機能 — InlineViz等（未着手）
12. 横断情報
    - 12-1. 依存関係
    - 12-2. 開発期間サマリー
    - 12-3. リスクと緩和策
    - 12-4. 開発ルール（→ memos/開発ルール.md）
    - 12-5. 変更履歴

---

## 0. 全体像

### プロジェクト情報

| 項目 | 内容 |
|------|------|
| **プロダクト名** | Decision Intelligence Platform (DIP) |
| **目的** | 企業データを活用した意思決定支援AIチャット |
| **リポジトリ** | https://github.com/ksea134/decision-intelligence-platform |
| **Streamlit Cloud** | https://dip134.streamlit.app/ |
| **GCP Project** | `decision-support-ai` |
| **Python Version** | 3.11 |

### 事業フェーズとPhaseの対応（2026-03-20追加）

DIPの開発・展開は大きく3つの事業フェーズに分かれる。各Phaseはこの事業フェーズに紐づく。

| 事業フェーズ | 内容 | 対応するPhase | AI Ops |
|-------------|------|--------------|--------|
| **1. 開発・検証** | 社内で作って形にする。機能開発・バグ修正・デモ準備 | Phase 0〜4（← 今ここ） | — |
| **2. PoC・実証実験** | 個別のお客様にお試しで使ってもらい評価を受ける。エンタープライズUI・本番インフラが必要 | Phase 5〜6 + AI Ops A・B | Phase A: ログ基盤（PoC開始前に必須）、Phase B: 監視・アラート（PoC中の障害即対応） |
| **3. 本番運用** | 正式契約、継続的・永続的に使ってもらう。SLA保証・コスト管理・品質評価が必要 | Phase 7〜8 + AI Ops C・D | Phase C: コスト管理ダッシュボード、Phase D: 回答品質自動評価・Human in the Loop |

> **注意**: 「本番機」「エンタープライズ版」はPoC段階（事業フェーズ2）から必要になるが、PoCはあくまで評価目的であり、本番運用（事業フェーズ3）とは位置づけが異なる。

### ロードマップサマリー

| Phase | 名称 | 期間 | ステータス | 備考 |
|-------|------|------|-----------|------|
| 0 | 基盤準備・仕様策定 | 1週間 | ✅ 完了 | SPEC_v1.md作成 |
| 1 | Agent Router | 1週間 | ✅ 完了 | LangGraph統合、v1.1.0-phase1 |
| 2 | Memory Store統合 | 1週間 | ⏭️ スキップ | コスト削減のため延期。当面インメモリ運用 |
| 3 | Vertex AI Search統合 | 2週間 | ✅ 完了 | v3.6.1-stable |
| 4A | Agent Builder基盤 | 2週間 | ✅ 完了 | ADK統合、v4.0.0-stable |
| 4B | エコシステム連携 | 2週間 | 🔶 一部完了 | Gemini Flash/Pro使い分け完了。Model Garden連携はPhase 5後 |
| 5 | エンタープライズUI移行 | 3週間 | 🔄 一部完了 | Cloud Runデプロイ済み・IAP設定完了（2026-03-20）。残作業: カスタムドメイン設定、テスト全28項目実行、旧コード整理 |
| 6 | Governance層実装 | 2週間 | ⬜ 未着手 | Dataplex。PoC開始前に完了 |
| 7A | AI Ops: ログ基盤 | — | ⬜ 未着手 | **Phase 5と同時**。Cloud Logging/Trace連携 |
| 7B | AI Ops: 監視・アラート | — | ⬜ 未着手 | **Phase 5完了直後**。Cloud Monitoring/Alerting |
| 7C | AI Ops: コスト管理 | — | ⬜ 未着手 | 運用安定後。Billing Export + Looker |
| 7D | AI Ops: 品質評価 | — | ⬜ 未着手 | 中長期。Vertex AI Evaluation + Human in the Loop |
| 8 | 高度機能（InlineViz等） | 2週間 | ⬜ 未着手 | 文中描画 |

**総開発期間**: 約18週間（4.5ヶ月）

### アーキテクチャ（7層構造）

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        統合運用: Kyndryl Bridge                         │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
┌───────────────────────┬───────────┴───────────┬───────────────────────┐
│ Security & Governance │      AI Core System    │  AI Ops & Observability│
│      守りの要         │                        │    進化と品質の監視    │
├───────────────────────┼────────────────────────┼───────────────────────┤
│ ・VPC Service Controls│  UI/UX層               │ ・Kyndryl Bridge      │
│ ・Cloud Identity/IAM  │   └ Cloud Run + IAP    │   Connector           │
│ ・Cloud DLP           │   └ Grounding機能      │ ・Cloud Monitoring    │
│ ・Cloud KMS(CMKS)     │                        │   / Logging           │
│                       │  Orchestration層       │ ・Vertex AI Evaluation│
│                       │   └ Vertex AI Agent    │ ・Human in the loop   │
│                       │     Builder            │ ・FinOps/Cost Mgmt    │
│                       │   └ Reasoning Engine   │                       │
│                       │   └ Memory Store       │                       │
│                       │   └ Vertex AI Search   │                       │
│                       │                        │                       │
│                       │  Model層               │                       │
│                       │   └ Gemini 2.5 Pro     │                       │
│                       │   └ Gemini 2.5 Flash   │                       │
│                       │   └ Model Garden       │                       │
│                       │                        │                       │
│                       │  Governance層          │                       │
│                       │   └ Dataplex           │                       │
│                       │                        │                       │
│                       │  Storage層             │                       │
│                       │   └ BigQuery Storage   │                       │
│                       │   └ BigLake            │                       │
│                       │   └ Cloud Storage      │                       │
│                       │                        │                       │
│                       │  Ingestion層           │                       │
│                       │   └ Data Fusion        │                       │
│                       │   └ Dataflow           │                       │
└───────────────────────┴────────────────────────┴───────────────────────┘
                                    │
┌─────────────────────────────────────────────────────────────────────────┐
│ DataSource: SAP, Salesforce, ServiceNow, DB, Excel, PPT, Word, PDF...  │
└─────────────────────────────────────────────────────────────────────────┘
```

### 技術的決定事項（確定）

| 項目 | 決定内容 | 理由 |
|------|---------|------|
| 開発方針 | 新規ファイル構成（並行開発） | 既存動作を維持しつつ移行 |
| Reasoning Engine | LangGraph → ADK | Google Cloud推奨。Phase 4Aで移行済み |
| 短期記憶 | インメモリ（将来: Redis Memorystore） | Phase 2スキップ。当面はst.session_stateで運用 |
| 長期記憶 | Vertex AI Search | RAG統合、Grounding機能、GCPマネージド |
| メインモデル | Gemini 2.5 Flash / Pro | Flash=高速低コスト、Pro=高精度。エージェント別に自動選択 |
| 複雑推論（将来） | Claude Opus / Sonnet | Model Garden経由。Phase 5後に実施 |
| UI | Streamlit → Cloud Run + IAP | エンタープライズ対応 |

---

## 1. フォルダ構成

```
dip/
├── app.py                              # エントリポイント
├── requirements.txt
├── pyproject.toml
├── .streamlit/secrets.toml             # API Keys
│
├── config/
│   ├── app_config.py                   # AppConfig, UIConfig, PathConfig
│   └── cloud_config.py                 # CloudConfig
│
├── ui/
│   └── components/
│       ├── chat.py                     # チャットUI
│       ├── sidebar.py                  # サイドバー
│       ├── smart_cards.py              # スマートカード
│       ├── infographic.py              # インフォグラフィック
│       └── debug_panel.py              # デバッグパネル
│
├── orchestration/
│   ├── reasoning_engine.py             # V1エンジン（安定版）
│   ├── reasoning_engine_v2.py          # V2（Agent Router統合）
│   ├── agents/
│   │   ├── data_agent.py              # BigQuery/GCS接続
│   │   └── router_agent.py            # 意図分類ルーター（キーワード分類）
│   ├── adk/
│   │   └── runner.py                  # ADKエンジン（Phase 4A）
│   └── memory/
│       └── session_memory.py           # セッション記憶（インメモリ）
│
├── domain/
│   ├── models.py                       # ドメインモデル（ChatMessage等）
│   ├── sql_validator.py                # SQLバリデーション
│   ├── prompt_builder.py               # プロンプト構築
│   └── response_parser.py              # レスポンス解析
│
├── infra/
│   ├── bigquery_service.py             # BigQuery接続
│   ├── gcs_service.py                  # GCS接続
│   ├── file_loader.py                  # ローカルファイル読込
│   ├── vertex_ai_search.py            # Vertex AI Search（Phase 3）
│   └── _smart_card_defaults.py         # スマートカードデフォルト
│
└── data/                               # 企業別データ
    ├── companies.csv
    └── {企業名}/                       # 各企業のデータフォルダ
```

---

## 2. Phase 0: 基盤準備・仕様策定 ✅ 完了

**完了日:** 2026-03-15

### 概要
既存の単一ファイル実装（dip-f02_1.py, 2,638行）から仕様を抽出し、新規アーキテクチャの設計を行った。

### 成果物
- **SPEC_v1.md** — 既存コードから20機能を特定・文書化
- **SPEC_inline_viz_future.md** — 将来機能（文中描画）の設計
- **アーキテクチャ7層構造** — 確定

### コア機能（20種）

| # | 機能名 | 概要 |
|---|--------|------|
| F01 | マルチ企業対応チャット | companies.csvで企業切替、履歴保持 |
| F02 | BigQuery連携 | スキーマ取得 + SQL自動生成 + 実行 |
| F03 | GCS連携 | .txt/.mdファイルをコンテキスト注入 |
| F04 | ローカルファイル読込 | 7ディレクトリ対応 |
| F05 | ストリーミング回答 | Tool Callループ含む |
| F06 | 思考ロジック生成 | 4ステップの思考プロセス |
| F07 | インフォグラフィック生成 | JSON→HTML Exec Summary |
| F08 | 深掘り質問生成 | フォローアップ3件 |
| F09 | スマートカード | 5種のショートカットプロンプト |
| F10 | 質問履歴 | 直近5件、再実行・削除 |
| F11 | PNG保存 | html2canvas |
| F12 | PDFエクスポート | html2pdf |
| F13 | テキストコピー | クリップボード |
| F14 | テキストDL | .txt出力 |
| F15 | データソースバッジ | BQ/GCS/ローカル表示 |
| F16 | 接続エラーバナー | 警告UI |
| F17 | 稼働状況パネル | リアルタイム表示 |
| F18 | BQ実行ログパネル | SQL/件数表示 |
| F19 | Grounding | [FILES:]タグ引用 |
| F20 | チャートレンダリング | bar/line/pie/scatter/table |

---

## 3. Phase 1: Agent Router ✅ 完了

**完了日:** 2026-03-16 / **バージョン:** v1.1.0-phase1

### 概要
LangGraphを用いた思考フロー制御の基盤を構築。ユーザーの意図を分類し、適切なエージェントを呼び出す仕組みを実装。

### 開発理由
- 「売上が落ちている」→「要因分析エージェント」といった複雑な思考フローを実現
- 単純な質問応答から高度な意思決定支援への進化に必須
- Orchestration層の中核として他の全機能の基盤

### 成果物

```
orchestration/
├── reasoning_engine_v2.py      # ReasoningEngineV2（USE_AGENT_ROUTERフラグで切替）
├── agents/
│   ├── router_agent.py         # LLM Router（意図分類）
│   ├── analysis_agent.py       # AnalysisAgent
│   ├── comparison_agent.py     # ComparisonAgent
│   ├── forecast_agent.py       # ForecastAgent
│   └── general_agent.py        # GeneralAgent
├── graph/
│   ├── state.py                # DIPState（TypedDict）
│   └── workflow.py             # LangGraph StateGraph
└── memory/
    └── session_memory.py       # SessionMemory（インメモリ）
```

### LangGraph StateGraph構造
```python
from langgraph.graph import StateGraph

class DIPState(TypedDict):
    messages: list[Message]
    intent: str                # analysis | comparison | forecast | general
    current_agent: str
    context: dict
    final_response: str

workflow = StateGraph(DIPState)
workflow.add_node("intent_classifier", classify_intent)
workflow.add_node("analysis_agent", run_analysis)
workflow.add_node("comparison_agent", run_comparison)
workflow.add_node("forecast_agent", run_forecast)
workflow.add_node("general_agent", run_general)
workflow.add_conditional_edges(
    "intent_classifier",
    route_to_agent,
    {
        "analysis": "analysis_agent",
        "comparison": "comparison_agent",
        "forecast": "forecast_agent",
        "general": "general_agent"
    }
)
```

### 意図分類プロンプト（router_agent.py）
```python
ROUTER_PROMPT = """
以下のユーザー入力を分析し、最も適切なエージェントを選択してください。

カテゴリ:
- analysis: データ分析、傾向把握、要因分析
- comparison: 比較、対比、ベンチマーク
- forecast: 予測、シミュレーション、将来推定
- general: 一般的な質問、説明、その他

ユーザー入力: {user_input}

回答は以下のJSON形式で:
{{"intent": "カテゴリ名", "confidence": 0.0-1.0, "reasoning": "判断理由"}}
"""
```

### テスト結果
```
tests/test_agent_router.py ... 15/15 passed
```

---

## 4. Phase 2: Memory Store統合 ⏭️ スキップ

**決定日:** 2026-03-18 / **理由:** コスト削減のため延期。当面インメモリで運用。

### 概要
短期記憶（会話履歴）をRedis Memorystoreで永続化し、セッション間での文脈維持を実現する。

### 開発理由
- 現行の`st.session_state`はStreamlit依存かつ揮発性
- エンタープライズ版ではCloud Run + IAPへの移行を予定しており、外部メモリストアが必須
- 本番運用においてセッションの復元・共有が必要

### 現状実装（インメモリ版）
```python
class SessionMemory:
    """現在: インメモリ実装 / 将来: Redis Memorystore（drop-in replacement）"""
    def __init__(self, session_id: str):
        self.session_id = session_id
        self._messages: list[ChatMessage] = []
    def add_message(self, message: ChatMessage) -> None: ...
    def get_history(self) -> list[ChatMessage]: ...
    def build_gemini_history(self) -> list[types.Content]: ...
    def clear(self) -> None: ...
```

### 将来の設計（Phase 5以降で実施）

```python
class MemoryBackend(ABC):
    @abstractmethod
    async def get_conversation(self, session_id: str) -> list[ChatMessage]: ...
    @abstractmethod
    async def save_message(self, session_id: str, message: ChatMessage) -> None: ...

class InMemoryBackend(MemoryBackend): ...   # 開発/テスト用
class RedisMemoryBackend(MemoryBackend): ... # 本番用
```

---

## 5. Phase 3: Vertex AI Search統合 ✅ 完了

**完了日:** 2026-03-18 / **バージョン:** v3.6.1-stable

### 概要
Vertex AI Searchを導入し、過去の質問・回答を長期記憶として保持。類似事例の検索により回答精度を向上させる。

### 開発理由
- 過去の意思決定事例を活用した回答生成
- 「以前同様の質問があった」という文脈の提供
- 企業固有のナレッジベース構築への第一歩

### 技術的説明
```python
from google.cloud import discoveryengine_v1 as discoveryengine

class VertexAISearchClient:
    def __init__(self, project_id, data_store_id, location="global"):
        self._doc_client = discoveryengine.DocumentServiceClient()
        self._search_client = discoveryengine.SearchServiceClient()

    def store(self, question, answer, company, ...): ...  # Q&A保存
    def search(self, query, company, ...): ...             # 類似検索
```

### GCPリソース構成
```
┌───────────────────────────────────────────────────────────┐
│ Vertex AI Search                                          │
│  ┌─────────────────────────────────────────────────────┐  │
│  │ Data Store: dip-knowledge-store                     │  │
│  │ - Type: Unstructured documents                      │  │
│  │ - Source: GCS (gs://dsa-knowledge-base/)            │  │
│  └─────────────────────────────────────────────────────┘  │
│  ┌─────────────────────────────────────────────────────┐  │
│  │ Search App: dip-search-app                          │  │
│  │ - Type: Search                                      │  │
│  │ - Features: Semantic search + 企業名フィルタ        │  │
│  └─────────────────────────────────────────────────────┘  │
└───────────────────────────────────────────────────────────┘
```

**詳細仕様:** → `memos/DIPアーキテクチャー概要.md` セクション3

---

## 6. Phase 4A: Agent Builder基盤 ✅ 完了

**完了日:** 2026-03-18 / **バージョン:** v4.0.0-stable

### 概要
Google ADK（Agent Development Kit）ベースのエージェント構造を実装。USE_ADK_ENGINEフラグで従来エンジンとの切替が可能。

### 開発理由
- GCPマネージドサービスによる運用負荷軽減
- オートスケーリング、高可用性の自動化
- Google社のエンタープライズサポート活用

### 技術的説明
```python
from google.adk.agents import LlmAgent

class ADKReasoningEngine:
    """ADKベースのエージェントエンジン"""
    # USE_ADK_ENGINE=True で有効化
    # google-adkが未インストールの環境では自動的にReasoningEngineにフォールバック
```

### Playbook定義例
```yaml
name: decision-support-agent
description: 意思決定支援エージェント
steps:
  - step: classify_intent
    action: llm_call
  - step: route_to_specialist
    condition: intent == "data_analysis"
    action: call_tool
    tool: bigquery_analyst
```

---

## 7. Phase 4B: エコシステム連携 🔶 一部完了

**Gemini Flash/Pro使い分け:** 完了（2026-03-18）
**Model Garden連携:** 未着手（Phase 5の後に実施）

### 概要
Model Gardenを通じた外部モデル（Claude等）の統合、A2Aプロトコルによる外部エージェント連携、MCPによるツール接続標準化。

### 完了済み: モデル使い分け

| エージェント | モデル | 理由 |
|------------|--------|------|
| ルーター | Gemini 2.5 Flash | 分類だけなので高速・低コスト |
| 汎用回答 | Gemini 2.5 Flash | シンプルな質問は高速で十分 |
| 要因分析 | Gemini 2.5 Pro | 5 Whys等の深い推論が必要 |
| 比較分析 | Gemini 2.5 Pro | 多角的な分析が必要 |
| 予測分析 | Gemini 2.5 Pro | シナリオ分析で精度が重要 |

設定ファイル: `orchestration/adk/agent_definition.py`

### 未着手: Model Garden連携

```python
# 将来の実装イメージ
class ModelGardenService:
    async def call_claude(self, messages, model="claude-sonnet-4-6") -> str:
        client = anthropic.AnthropicVertex(project_id=self.project_id, region=self.location)
        response = client.messages.create(model=model, max_tokens=4096, messages=messages)
        return response.content[0].text

    def select_model(self, task_type: str) -> str:
        model_routing = {
            "complex_reasoning": "claude-opus-4-6",
            "code_generation": "claude-sonnet-4-6",
            "fast_response": "gemini-2.5-flash",
            "data_analysis": "gemini-2.5-pro",
        }
        return model_routing.get(task_type, "gemini-2.5-flash")
```

### 未着手: A2A / MCP

| 機能 | 説明 | 技術要素 |
|------|------|----------|
| A2Aプロトコル対応 | 外部エージェントとの通信標準 | A2A Protocol v0.3+ |
| A2A Server実装 | DIPをA2Aサーバーとして公開 | Agent Card, JSON-RPC |
| MCP統合 | ツール接続の標準化 | Model Context Protocol |

#### プロトコル関係図
```
┌─────────────────────────────────────────────────────────────────┐
│                    DIP (Decision Intelligence Platform)         │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                   Agent Engine (ADK)                      │  │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐     │  │
│  │  │ 要因分析 │  │シミュレ │  │レポート │  │ 一般QA  │     │  │
│  │  │ Agent   │  │ Agent   │  │ Agent   │  │ Agent   │     │  │
│  │  └────┬────┘  └────┬────┘  └────┬────┘  └────┬────┘     │  │
│  └───────┼───────────┼───────────┼───────────┼──────────────┘  │
│          │           │           │           │                  │
│  ┌───────┴───────────┴───────────┴───────────┴──────────────┐  │
│  │                    Model Router                           │  │
│  │  Gemini Pro | Gemini Flash | Claude Sonnet | Claude Opus  │  │
│  └───────────────────────────────────────────────────────────┘  │
│          │                                     │                │
│          │ MCP (Tools)                         │ A2A (Agents)   │
│          ▼                                     ▼                │
│  ┌───────────────────┐               ┌───────────────────────┐ │
│  │ BigQuery MCP      │               │ Salesforce Agentforce │ │
│  │ Google Maps MCP   │               │ SAP Joule             │ │
│  │ Custom MCP Servers│               │ ServiceNow Agent      │ │
│  └───────────────────┘               └───────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

---

## 8. Phase 5: エンタープライズUI移行 ⬜ 未着手

### 概要
Streamlitから脱却し、Cloud Run + IAP (Identity-Aware Proxy) による独自Webアプリケーションへ移行。

### 開発理由
- Streamlitはエンタープライズ用途には機能不足（認証、アクセス制御）
- GCP IAPによるゼロトラスト認証の実現
- カスタムUIによるUX最適化

### 機能詳細

| 機能 | 説明 | 技術要素 |
|------|------|----------|
| Cloud Run デプロイ | コンテナ化されたWebアプリ | Docker, Cloud Run |
| IAP統合 | Google Workspace認証 | IAP, Cloud Identity |
| フロントエンド開発 | React/Next.js ベースUI | React, TypeScript |
| SSE/WebSocket | ストリーミング回答対応 | Server-Sent Events |
| API Gateway | バックエンドAPI設計 | FastAPI, API Gateway |

### アーキテクチャ
```
┌────────────────────────────────────────────────────────────┐
│                    Cloud Load Balancer                     │
│                          + IAP                             │
└─────────────────────────┬──────────────────────────────────┘
                          │
┌─────────────────────────▼──────────────────────────────────┐
│                      Cloud Run                              │
│  ┌─────────────────┐  ┌─────────────────┐                  │
│  │ Frontend        │  │ Backend API     │                  │
│  │ (Next.js)       │  │ (FastAPI)       │                  │
│  │ - React UI      │  │ - /api/chat     │                  │
│  │ - SSE Client    │  │ - /api/export   │                  │
│  │ - Chart.js      │  │ - /api/history  │                  │
│  └─────────────────┘  └─────────────────┘                  │
└────────────────────────────────────────────────────────────┘
                          │
        ┌─────────────────┼─────────────────┐
        ▼                 ▼                 ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│ Redis        │  │ BigQuery     │  │ GCS          │
│ Memorystore  │  │              │  │              │
└──────────────┘  └──────────────┘  └──────────────┘
```

### 開発時間
- 期間: 3週間 / 工数: 120時間

### 併せて実施する作業
- キャッシュのStreamlit依存解消（→ `memos/DIPアーキテクチャー概要.md` セクション4参照）
- Memory Store統合（Phase 2の内容をここで実施）

---

## 9. Phase 6: Governance層実装 ⬜ 未着手

### 概要
Dataplexを統合し、データカタログ、アクセス制御、データリネージュを実現。

### 開発理由
- 複数企業データのセキュアな分離管理
- 誰がどのデータにアクセスしたかの監査証跡
- 機密データの自動マスキング（Cloud DLP連携）
- コンプライアンス要件への対応

### 機能詳細

| 機能 | 説明 | 技術要素 |
|------|------|----------|
| データカタログ | BQ/GCSリソースの自動登録 | Dataplex Catalog |
| ゾーン管理 | 企業別データゾーンの定義 | Dataplex Zones |
| アクセス制御 | Row/Columnレベルのアクセス制御 | BigQuery Row-level Security |
| DLP統合 | 機密情報の自動検出・マスキング | Cloud DLP |
| リネージュ | データの出自・変換履歴追跡 | Dataplex Lineage |

### 開発時間
- 期間: 2週間 / 工数: 80時間

---

## 10. Phase 7: Observability & FinOps ⬜ 未着手

### 概要
Cloud Monitoring統合、Vertex AI Evaluation、コスト監視を実装。

### 開発理由
- 本番運用における品質監視の必須要件
- LLM回答精度の継続的評価
- APIコスト（特にGemini/Claude）の可視化と最適化

### 機能詳細

| 機能 | 説明 | 技術要素 |
|------|------|----------|
| Metrics収集 | レイテンシ、エラー率、スループット | Cloud Monitoring |
| ログ統合 | 構造化ログの集約 | Cloud Logging |
| トレーシング | リクエストの分散トレース | Cloud Trace |
| 回答品質評価 | ハルシネーション検出、正確性評価 | Vertex AI Evaluation |
| コスト監視 | トークン使用量、API課金の可視化 | Billing Export + Looker |
| アラート設定 | 異常検知時の通知 | Cloud Alerting |

### ダッシュボード構成（イメージ）
```
┌─────────────────────────────────────────────────────────────┐
│                DIP Operations Dashboard                      │
├─────────────────┬───────────────────┬───────────────────────┤
│ Response Time   │ Error Rate        │ Active Sessions       │
│ Avg: 2.3s       │ 0.5%              │ 127                   │
│ P95: 5.1s       │ ▼ 0.2% from last  │ ▲ 15% from last hour  │
├─────────────────┴───────────────────┴───────────────────────┤
│ Token Usage (24h) by Model                                   │
│ Gemini Pro: ████████░░ 1.2M | Claude: ████░░░░ 500K         │
│ Gemini Flash: ██████████ 2.1M | Total Cost: $342            │
├─────────────────────────────────────────────────────────────┤
│ Answer Quality Score                                         │
│ Accuracy: 4.2/5 | Completeness: 3.9/5 | Hallucination: 2%   │
└─────────────────────────────────────────────────────────────┘
```

### 開発時間
- 期間: 2週間 / 工数: 80時間

---

## 11. Phase 8: 高度機能（InlineViz等） ⬜ 未着手

### 概要
文中描画機能（InlineViz）やその他の高度なUX機能を実装。意思決定支援AIとしての差別化機能。

### 開発理由
- 説明と図の一体化によるユーザー理解度向上
- 競合との差別化要素
- SPEC_inline_viz_future.mdで設計済み

### LLM出力形式（タグベース）
```markdown
売上を分析すると、Q3に大きな伸びが見られます。

<viz type="bar" title="四半期別売上">
{"labels": ["Q1", "Q2", "Q3", "Q4"], "data": [120, 145, 210, 180], "unit": "百万円"}
</viz>

この傾向の要因として、以下の3点が考えられます...
```

### 対応する描画タイプ

| type | 用途 | レンダラー |
|------|------|-----------|
| bar, line, pie, scatter | データチャート | Plotly |
| flowchart | フローチャート | Mermaid |
| sequence | シーケンス図 | Mermaid |
| table | データテーブル | HTML Table |
| diagram | カスタム図解 | SVG直接描画 |

### VizTagParser
```python
@dataclass
class StreamChunk:
    content_type: str  # "text" | "viz"
    content: str
    viz_config: dict | None = None

class VizTagParser:
    VIZ_PATTERN = re.compile(
        r'<viz\s+type="(\w+)"(?:\s+title="([^"]*)")?\s*>(.*?)</viz>',
        re.DOTALL
    )
    def parse_stream(self, text: str) -> Generator[StreamChunk, None, None]: ...
```

### 開発時間
- 期間: 2週間 / 工数: 80時間

---

## 12. 横断情報

### 12-1. 依存関係

```
Phase 0 ✅
    │
    └──► Phase 1: Agent Router ✅
              │
              ├──► Phase 2: Memory Store ⏭️ スキップ
              │         │
              │         └──► Phase 4A: Agent Builder ✅
              │                   │
              │                   └──► Phase 4B: エコシステム連携 🔶
              │                              │
              │                              └──► Phase 5: Enterprise UI ⬜
              │                                         │
              │                                         └──► Phase 6: Governance ⬜
              │                                                    │
              │                                                    └──► Phase 7 ⬜
              │
              └──► Phase 3: Vertex AI Search ✅
                        │
                        └──► Phase 8: Advanced Features ⬜
```

| Phase | 前提条件 | 理由 |
|-------|----------|------|
| 1 | Phase 0完了 | アーキテクチャ確定後 |
| 2 | Phase 1完了 | Agent Router上でMemory機能 |
| 3 | Phase 1完了 | Vertex AI Searchは独立して進行可能 |
| 4A | Phase 2完了 | Memory Store設計がAgent Engine統合に影響 |
| 4B | Phase 4A完了 | Agent基盤がないとエコシステム連携不可 |
| 5 | Phase 4B完了 | 全Agent機能が揃ってからUI構築 |
| 6 | Phase 5完了 | UI経由でのデータアクセスパターンが確定後 |
| 7 | Phase 6完了 | Governance下でのメトリクス収集が正確 |
| 8 | Phase 3完了 | Vertex AI Searchによる類似事例がInlineVizに必要 |

### 12-2. 開発期間サマリー

| Phase | 名称 | 期間 | 累計 |
|-------|------|------|------|
| 0 | 基盤準備 ✅ | 1週間 | 1週間 |
| 1 | Agent Router ✅ | 1週間 | 2週間 |
| 2 | Memory Store ⏭️ | — | — |
| 3 | Vertex AI Search ✅ | 2週間 | 4週間 |
| 4A | Agent Builder ✅ | 2週間 | 6週間 |
| 4B | エコシステム連携 🔶 | 2週間 | 8週間 |
| 5 | Enterprise UI | 3週間 | 11週間 |
| 6 | Governance | 2週間 | 13週間 |
| 7 | Observability | 2週間 | 15週間 |
| 8 | Advanced Features | 2週間 | 17週間 |

### 12-3. リスクと緩和策

| リスク | 影響度 | 緩和策 |
|--------|--------|--------|
| Gemini API仕様変更 | 高 | google-genai SDKの抽象化、バージョン固定 |
| Agent Builder機能不足 | 中 | LangGraphとのハイブリッド構成維持 |
| Vertex AI Search遅延 | 低 | キャッシュ戦略、クエリ最適化 |
| コスト超過 | 中 | FinOps早期導入、Flash優先利用 |
| Claude API クォータ制限 | 中 | Model Routerによるフォールバック |
| A2Aプロトコル仕様変更 | 中 | バージョン固定、抽象化レイヤー |
| 外部エージェント障害 | 低 | タイムアウト設定、ローカルフォールバック |

### 12-4. 開発ルール・セキュリティ仕様・テスト項目

→ `memos/開発ルール.md` に一元管理。設計ルール、Gemini APIルール、セキュリティ仕様、データソース受け渡しルール、バージョン管理ルール、アーキテクチャ変更後のテスト項目を参照。

### 12-5. 変更履歴

| バージョン | 日付 | 変更内容 |
|-----------|------|----------|
| 1.0 | 2026-03-17 | 初版作成 |
| 1.1 | 2026-03-17 | Phase 4を4A/4Bに分割、Model Garden・A2A対応追加 |
| 2.0 | 2026-03-17 | 過去チャット履歴・全ドキュメントを統合した決定版 |
| 2.1 | 2026-03-18 | 「Vertex AI Vector Search」→「Vertex AI Search」に統一 |
| **2.2** | **2026-03-19** | **全Phase状況を最新化。全体像・目次追加。構造を再編成** |
