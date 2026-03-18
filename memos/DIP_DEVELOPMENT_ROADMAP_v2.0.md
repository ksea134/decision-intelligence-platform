# Decision Intelligence Platform (DIP) — 開発ロードマップ
> バージョン: 2.0  
> 作成日: 2026-03-17  
> アーキテクチャ準拠: 意思決定支援AI 7層構造  
> ベースドキュメント: SPEC_v1.md, SPEC_inline_viz_future.md, DIP_DEVELOPMENT_ROADMAP_v1_1.md

---

## 変更履歴

| バージョン | 日付 | 変更内容 |
|-----------|------|----------|
| 1.0 | 2026-03-17 | 初版作成 |
| 1.1 | 2026-03-17 | Phase 4を4A/4Bに分割、Model Garden・A2A対応追加 |
| **2.0** | **2026-03-17** | **過去チャット履歴・全ドキュメントを統合した決定版。Phase 1完了を反映、技術的詳細を追加、GitHub/Streamlit Cloud情報を追加** |

---

## 全体概要

### プロジェクト情報

| 項目 | 内容 |
|------|------|
| **プロダクト名** | Decision Intelligence Platform (DIP) |
| **目的** | 企業データを活用した意思決定支援AIチャット |
| **現行コード** | `dip-f02_1.py` (2,638行) → 新アーキテクチャへ移行中 |
| **リポジトリ** | https://github.com/ksea134/decision-intelligence-platform |
| **Streamlit Cloud** | https://decision-intelligence-platform-8dq3z4phbogxy7tm6akabt.streamlit.app |
| **GCP Project** | `decision-support-ai` |
| **Python Version** | 3.11（推奨）、現行 3.9.6 |

### ロードマップサマリー

| Phase | 名称 | 期間 | ステータス | 備考 |
|-------|------|------|-----------|------|
| 0 | 基盤準備・仕様策定 | 1週間 | ✅ 完了 | SPEC_v1.md作成 |
| 1 | Agent Router | 1週間 | ✅ 完了 | LangGraph統合、v1.1.0-phase1、V1統合済み |
| 2 | Memory Store統合 | 1週間 | ⏭️ スキップ | 当面インメモリで運用。コスト削減のため延期 |
| 3 | Vertex AI Search統合 | 2週間 | ✅ 完了 | Vertex AI Search、v3.6.1-stable |
| 4A | Agent Builder基盤 | 2週間 | ✅ 完了 | ADK移行、v4.0.0-stable |
| 4B | エコシステム連携 | 2週間 | ⬜ 未着手 | Model Garden / A2A / MCP |
| 5 | エンタープライズUI移行 | 3週間 | ⬜ 未着手 | Cloud Run + IAP |
| 6 | Governance層実装 | 2週間 | ⬜ 未着手 | Dataplex |
| 7 | Observability & FinOps | 2週間 | ⬜ 未着手 | Cloud Monitoring |
| 8 | 高度機能（InlineViz等） | 2週間 | ⬜ 未着手 | 文中描画 |

**総開発期間**: 約18週間（4.5ヶ月）

---

## アーキテクチャ（7層構造）

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
│                       │   └ Vertex AI Search      │                       │
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

---

## 新アーキテクチャ フォルダ構成

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
│   ├── reasoning_engine.py             # v1（既存・安定版）
│   ├── reasoning_engine_v2.py          # v2（Agent Router統合）← Phase 1成果物
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── data_agent.py               # BigQuery/GCS接続
│   │   ├── router_agent.py             # 意図分類ルーター
│   │   ├── analysis_agent.py           # 分析エージェント
│   │   ├── comparison_agent.py         # 比較エージェント
│   │   ├── forecast_agent.py           # 予測エージェント
│   │   └── general_agent.py            # 汎用エージェント
│   ├── graph/
│   │   ├── state.py                    # LangGraph State定義
│   │   └── workflow.py                 # LangGraph Workflow
│   └── memory/
│       └── session_memory.py           # セッション記憶（Phase 2でRedis化）
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
│   ├── vector_search_client.py         # Vertex AI Search（Phase 3）
│   └── _smart_card_defaults.py         # スマートカードデフォルト
│
├── tests/
│   ├── test_agent_router.py            # Agent Routerテスト
│   ├── test_sql_validator.py
│   └── ...
│
└── data/                               # 企業別データ
    ├── companies.csv
    ├── mazda/
    ├── 7andi_audit/
    ├── 7andi_stock/
    ├── factory_demo/
    ├── muratec/
    ├── nippon_steel/
    ├── omron/
    └── taisei/
```

---

## Phase 0: 基盤準備・仕様策定 ✅ 完了

### 概要
既存の単一ファイル実装（dip-f02_1.py）から仕様を抽出し、新規アーキテクチャの設計を行った。

### 成果物
- **SPEC_v1.md** — 既存コードから20機能を特定・文書化
- **SPEC_inline_viz_future.md** — 将来機能（文中描画）の設計
- **アーキテクチャ7層構造** — 確定

### 機能一覧（SPEC_v1.mdより）

#### コア機能（20種）
| # | 機能名 | 概要 | 継承判定 |
|---|--------|------|----------|
| F01 | マルチ企業対応チャット | companies.csvで企業切替、履歴保持 | ✅ |
| F02 | BigQuery連携 | スキーマ取得 + SQL自動生成 + 実行 | ✅ |
| F03 | GCS連携 | .txt/.mdファイルをコンテキスト注入 | ✅ |
| F04 | ローカルファイル読込 | 7ディレクトリ対応 | ✅ |
| F05 | ストリーミング回答 | Tool Callループ含む | ✅ |
| F06 | 思考ロジック生成 | 4ステップの思考プロセス | ✅ |
| F07 | インフォグラフィック生成 | JSON→HTML Exec Summary | ✅ |
| F08 | 深掘り質問生成 | フォローアップ3件 | ✅ |
| F09 | スマートカード | 5種のショートカットプロンプト | ✅ |
| F10 | 質問履歴 | 直近5件、再実行・削除 | ✅ |
| F11 | PNG保存 | html2canvas | ✅ |
| F12 | PDFエクスポート | html2pdf | ✅ |
| F13 | テキストコピー | クリップボード | ✅ |
| F14 | テキストDL | .txt出力 | ✅ |
| F15 | データソースバッジ | BQ/GCS/ローカル表示 | ✅ |
| F16 | 接続エラーバナー | 警告UI | ✅ |
| F17 | 稼働状況パネル | リアルタイム表示 | ✅ |
| F18 | BQ実行ログパネル | SQL/件数表示 | ✅ |
| F19 | Grounding | [FILES:]タグ引用 | ✅ |
| F20 | チャートレンダリング | bar/line/pie/scatter/table | ✅ |

### 技術的決定事項（確定）

| 項目 | 決定内容 | 理由 |
|------|---------|------|
| 開発方針 | 新規ファイル構成（並行開発） | 既存動作を維持しつつ移行 |
| Reasoning Engine | LangGraph | Google Cloud推奨 |
| 短期記憶 | Redis Memorystore | スケーラブル、DIパターン |
| 長期記憶 | Vertex AI Search | 類似検索、GCP統合 |
| メインモデル | Gemini 2.5 Flash | コスト最適化 |
| 複雑推論 | Gemini 2.5 Pro / Claude | タスク特化 |
| UI | Streamlit → Cloud Run + IAP | エンタープライズ対応 |

### ステータス: ✅ 完了（2026-03-15）

---

## Phase 1: Agent Router ✅ 完了

### 概要
LangGraphを用いた思考フロー制御の基盤を構築。ユーザーの意図を分類し、適切なエージェントを呼び出す仕組みを実装。

### 開発理由
- 「売上が落ちている」→「要因分析エージェント」→「シミュレーションエージェント」といった複雑な思考フローを実現
- 単純な質問応答から高度な意思決定支援への進化に必須
- Orchestration層の中核として他の全機能の基盤

### 成果物

#### 新規ファイル
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

#### LangGraph StateGraph構造
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

#### 意図分類プロンプト（router_agent.py）
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

### 実機動作確認
- **Streamlit Cloud**: デプロイ済み
- **BigQuery接続**: 11テーブル認識
- **GCS接続**: 8ドキュメント取得
- **USE_AGENT_ROUTER**: `True` で新ルーター有効

### Git管理
```bash
git tag v1.1.0-phase1
git push origin v1.1.0-phase1
```

### ステータス: ✅ 完了（2026-03-16）

---

## Phase 2: Memory Store統合 ⏭️ スキップ

### 概要
短期記憶（会話履歴）をRedis Memorystoreで永続化し、セッション間での文脈維持を実現する。

### 開発理由
- 現行の`st.session_state`はStreamlit依存かつ揮発性
- エンタープライズ版ではCloud Run + IAPへの移行を予定しており、外部メモリストアが必須
- 本番運用においてセッションの復元・共有が必要

### 現状実装

#### SessionMemory（インメモリ版）
```python
# orchestration/memory/session_memory.py

class SessionMemory:
    """
    セッション記憶管理
    現在: インメモリ実装
    将来: Redis Memorystore（drop-in replacement）
    """
    
    def __init__(self, session_id: str):
        self.session_id = session_id
        self._messages: list[ChatMessage] = []
    
    def add_message(self, message: ChatMessage) -> None:
        self._messages.append(message)
    
    def get_history(self) -> list[ChatMessage]:
        return self._messages.copy()
    
    def build_gemini_history(self) -> list[types.Content]:
        """Gemini API用の履歴形式に変換"""
        # google-genai 1.47.0対応: types.Content/types.Part形式
        ...
    
    def clear(self) -> None:
        self._messages.clear()
```

### 設計（Phase 2完了時）

#### MemoryBackend抽象クラス（DIパターン）
```python
from abc import ABC, abstractmethod

class MemoryBackend(ABC):
    @abstractmethod
    async def get_conversation(self, session_id: str) -> list[ChatMessage]: ...
    
    @abstractmethod
    async def save_message(self, session_id: str, message: ChatMessage) -> None: ...
    
    @abstractmethod
    async def clear_conversation(self, session_id: str) -> None: ...
    
    @abstractmethod
    async def set_ttl(self, session_id: str, seconds: int) -> None: ...

class InMemoryBackend(MemoryBackend):
    """開発/テスト用"""
    def __init__(self):
        self._store: dict[str, list[ChatMessage]] = {}
    ...

class RedisMemoryBackend(MemoryBackend):
    """本番用 Redis Memorystore"""
    def __init__(self, redis_host: str, redis_port: int = 6379):
        self.client = redis.Redis(host=redis_host, port=redis_port, decode_responses=True)
    
    async def get_conversation(self, session_id: str) -> list[ChatMessage]:
        key = f"dip:session:{session_id}:messages"
        data = self.client.lrange(key, 0, -1)
        return [json.loads(msg) for msg in data]
    
    async def save_message(self, session_id: str, message: ChatMessage) -> None:
        key = f"dip:session:{session_id}:messages"
        self.client.rpush(key, json.dumps(asdict(message)))
    ...
```

### GCPリソース（プロビジョニング予定）
```
┌──────────────────────────────────────┐
│ VPC Network                          │
│  ┌────────────────────────────────┐  │
│  │ Memorystore for Redis          │  │
│  │ - Instance: dip-memory-store   │  │
│  │ - Tier: Standard (HA)          │  │
│  │ - Memory: 1GB (初期)           │  │
│  │ - Version: Redis 7.0           │  │
│  │ - Region: asia-northeast1      │  │
│  └────────────────────────────────┘  │
└──────────────────────────────────────┘
```

### タスク一覧

| # | タスク | ステータス |
|---|--------|-----------|
| 1 | GCP Memorystore for Redis インスタンス作成 | ⬜ 未着手 |
| 2 | RedisMemoryBackend クラス実装 | ⬜ 未着手 |
| 3 | SessionMemoryをBackend抽象化に対応 | ⬜ 未着手 |
| 4 | 環境変数でBackend切替（DI） | ⬜ 未着手 |
| 5 | 会話履歴の永続化テスト | ⬜ 未着手 |
| 6 | TTL管理（セッション有効期限） | ⬜ 未着手 |
| 7 | InMemoryBackend → RedisMemoryBackend 切替確認 | ⬜ 未着手 |

### 開発時間
- 期間: 1週間
- 工数: 40時間

### ステータス: ⏭️ スキップ（2026-03-18決定。当面インメモリで運用。コスト削減のため延期）

---

## Phase 3: Vertex AI Search統合 ✅ 完了

### 概要
Vertex AI Searchを導入し、過去の質問・回答を長期記憶として保持。類似事例の検索により回答精度を向上させる。

### 開発理由
- 過去の意思決定事例を活用した回答生成
- 「以前同様の質問があった」という文脈の提供
- 企業固有のナレッジベース構築への第一歩
- Phase 2完了後でないとメモリ設計と競合するリスク

### 機能詳細

| 機能 | 説明 | 技術要素 |
|------|------|----------|
| **F3-1: Embedding生成** | 質問/回答をベクトル化 | Vertex AI text-embedding-004 |
| **F3-2: Index作成** | ベクトルインデックスの構築 | Vertex AI Search Index |
| **F3-3: 類似検索** | 類似した過去事例の検索 | ANN (Approximate Nearest Neighbor) |
| **F3-4: コンテキスト注入** | 検索結果をシステムプロンプトに注入 | build_system_instruction拡張 |
| **F3-5: メタデータ管理** | 企業ID、日時、カテゴリ等の付与 | Filter対応 |

### 技術的説明
```python
# infra/vector_search_client.py

from vertexai.language_models import TextEmbeddingModel
from google.cloud import aiplatform

class EmbeddingService:
    def __init__(self):
        self.model = TextEmbeddingModel.from_pretrained("text-embedding-004")
    
    def embed(self, text: str) -> list[float]:
        embeddings = self.model.get_embeddings([text])
        return embeddings[0].values

class VectorSearchService:
    def __init__(self, index_endpoint: str, deployed_index_id: str):
        self.client = aiplatform.MatchingEngineIndexEndpoint(index_endpoint)
        self.deployed_index_id = deployed_index_id
    
    def find_similar(
        self, 
        query_embedding: list[float], 
        num_neighbors: int = 5,
        filter_: dict = None
    ) -> list[SimilarDocument]:
        response = self.client.find_neighbors(
            deployed_index_id=self.deployed_index_id,
            queries=[query_embedding],
            num_neighbors=num_neighbors,
            filter=filter_
        )
        return self._parse_response(response)
```

### GCPリソース構成
```
┌───────────────────────────────────────────┐
│ Vertex AI                                 │
│  ┌─────────────────────────────────────┐  │
│  │ Vertex AI Search                       │  │
│  │ - Index: dip-knowledge-index        │  │
│  │ - Dimensions: 768                   │  │
│  │ - Distance: DOT_PRODUCT_DISTANCE    │  │
│  │ - Shard: 1 (初期)                   │  │
│  └─────────────────────────────────────┘  │
│                                           │
│  ┌─────────────────────────────────────┐  │
│  │ Index Endpoint                      │  │
│  │ - Auto-scaling: 1-3 replicas        │  │
│  │ - Machine: n1-standard-16           │  │
│  └─────────────────────────────────────┘  │
└───────────────────────────────────────────┘
```

### 開発時間
- 期間: 2週間
- 工数: 80時間

### ステータス: ✅ 完了（2026-03-18、v3.6.1-stable）

---

## Phase 4A: Agent Builder基盤 ⬜ 未着手

### 概要
Vertex AI Agent Builderへの移行により、LangGraphで構築したフローをマネージド環境で実行。Agent Development Kit (ADK)を活用し、エンタープライズスケーリングの基盤を構築する。

### 開発理由
- GCPマネージドサービスによる運用負荷軽減
- オートスケーリング、高可用性の自動化
- Google社のエンタープライズサポート活用
- Phase 1-3完了後でないとAgent定義が不完全

### 機能詳細

| 機能 | 説明 | 技術要素 |
|------|------|----------|
| **F4A-1: ADK移行** | LangGraph → Agent Development Kit | ADK Python SDK |
| **F4A-2: Agent Engine デプロイ** | サーバーレス環境へのデプロイ | Agent Engine Runtime |
| **F4A-3: Tool登録** | BigQuery, GCS等のツール登録 | Extensions API |
| **F4A-4: Session管理** | Agent Builder Session統合 | Session API |
| **F4A-5: Memory Bank統合** | 長期記憶の永続化 | Memory Bank API |
| **F4A-6: Playbook作成** | 意思決定支援シナリオの定義 | Playbook YAML |
| **F4A-7: ハイブリッド構成** | 一部LangGraph + Agent Builder | フォールバック設計 |

### 技術的説明
```python
# Agent Development Kit (ADK) での実装
from google.adk import Agent

class DecisionSupportAgent:
    def create_agent(self) -> Agent:
        return Agent(
            model="gemini-2.5-flash",
            name="decision_support_agent",
            instruction=self.system_instruction,
            tools=[
                self.query_bigquery_tool,
                self.fetch_gcs_document_tool,
            ],
            description="企業の意思決定を支援するエージェント"
        )
```

### Playbook定義例
```yaml
name: decision-support-agent
description: 意思決定支援エージェント
steps:
  - step: classify_intent
    action: llm_call
    prompt: |
      ユーザーの意図を以下から分類してください:
      - data_analysis: データ分析が必要
      - simulation: シミュレーションが必要
      - general_qa: 一般的な質問
    
  - step: route_to_specialist
    condition: intent == "data_analysis"
    action: call_tool
    tool: bigquery_analyst
```

### 開発時間
- 期間: 2週間
- 工数: 80時間

### ステータス: ⬜ 未着手

---

## Phase 4B: エコシステム連携 ⬜ 未着手

### 概要
Model Gardenを通じた外部モデル（Claude等）の統合、A2Aプロトコルによる外部エージェント連携、MCPによるツール接続標準化を実装。

### 開発理由
- Gemini以外のモデル（Claude, Llama等）も用途に応じて選択可能
- 外部企業のエージェント（Salesforce Agentforce, SAP Joule等）との連携
- ツール接続の標準化（MCP）による拡張性向上
- Phase 4A完了後でないとAgent基盤が未整備

### 機能詳細

| 機能 | 説明 | 技術要素 |
|------|------|----------|
| **F4B-1: Model Garden統合** | Claude, Llama等の外部モデル利用 | Model Garden API |
| **F4B-2: モデルルーティング** | タスクに応じた最適モデル選択 | Model Router |
| **F4B-3: A2Aプロトコル対応** | 外部エージェントとの通信標準 | A2A Protocol v0.3+ |
| **F4B-4: A2A Server実装** | DIPをA2Aサーバーとして公開 | Agent Card, JSON-RPC |
| **F4B-5: A2A Client実装** | 外部エージェントの呼び出し | A2A Python SDK |
| **F4B-6: MCP統合** | ツール接続の標準化 | Model Context Protocol |

### 技術的説明

#### Model Garden統合（Claude利用例）
```python
import anthropic
from google.auth import default

class ModelGardenService:
    def __init__(self, project_id: str, location: str = "global"):
        self.project_id = project_id
        
    async def call_claude(self, messages: list, model: str = "claude-sonnet-4-6") -> str:
        """Vertex AI Model Garden経由でClaudeを呼び出し"""
        client = anthropic.AnthropicVertex(
            project_id=self.project_id,
            region=self.location,
        )
        response = client.messages.create(
            model=model,
            max_tokens=4096,
            messages=messages
        )
        return response.content[0].text
    
    def select_model(self, task_type: str) -> str:
        """タスクに応じて最適なモデルを選択"""
        model_routing = {
            "complex_reasoning": "claude-opus-4-6",
            "code_generation": "claude-sonnet-4-6", 
            "fast_response": "gemini-2.5-flash",
            "data_analysis": "gemini-2.5-pro",
        }
        return model_routing.get(task_type, "gemini-2.5-flash")
```

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

### 開発時間
- 期間: 2週間
- 工数: 80時間

### ステータス: ⬜ 未着手

---

## Phase 5: エンタープライズUI移行 ⬜ 未着手

### 概要
Streamlitから脱却し、Cloud Run + IAP (Identity-Aware Proxy) による独自Webアプリケーションへ移行。

### 開発理由
- Streamlitはエンタープライズ用途には機能不足（認証、アクセス制御）
- GCP IAPによるゼロトラスト認証の実現
- カスタムUIによるUX最適化
- SPEC_v1.mdで「差し替え対象」と明記

### 機能詳細

| 機能 | 説明 | 技術要素 |
|------|------|----------|
| **F5-1: Cloud Run デプロイ** | コンテナ化されたWebアプリ | Docker, Cloud Run |
| **F5-2: IAP統合** | Google Workspace認証 | IAP, Cloud Identity |
| **F5-3: フロントエンド開発** | React/Next.js ベースUI | React, TypeScript |
| **F5-4: SSE/WebSocket** | ストリーミング回答対応 | Server-Sent Events |
| **F5-5: API Gateway** | バックエンドAPI設計 | FastAPI, API Gateway |

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
- 期間: 3週間
- 工数: 120時間

### ステータス: ⬜ 未着手

---

## Phase 6: Governance層実装 ⬜ 未着手

### 概要
Dataplexを統合し、データカタログ、アクセス制御、データリネージュを実現。エンタープライズデータガバナンスの基盤を構築。

### 開発理由
- 複数企業データのセキュアな分離管理
- 誰がどのデータにアクセスしたかの監査証跡
- 機密データの自動マスキング（Cloud DLP連携）
- コンプライアンス要件への対応

### 機能詳細

| 機能 | 説明 | 技術要素 |
|------|------|----------|
| **F6-1: データカタログ** | BQ/GCSリソースの自動登録 | Dataplex Catalog |
| **F6-2: ゾーン管理** | 企業別データゾーンの定義 | Dataplex Zones |
| **F6-3: アクセス制御** | Row/Columnレベルのアクセス制御 | BigQuery Row-level Security |
| **F6-4: DLP統合** | 機密情報の自動検出・マスキング | Cloud DLP |
| **F6-5: リネージュ** | データの出自・変換履歴追跡 | Dataplex Lineage |

### 開発時間
- 期間: 2週間
- 工数: 80時間

### ステータス: ⬜ 未着手

---

## Phase 7: Observability & FinOps ⬜ 未着手

### 概要
Cloud Monitoring統合、Vertex AI Evaluation、コスト監視を実装。運用品質とコスト最適化の基盤を構築。

### 開発理由
- 本番運用における品質監視の必須要件
- LLM回答精度の継続的評価
- APIコスト（特にGemini/Claude）の可視化と最適化
- SLA/SLO管理の基盤

### 機能詳細

| 機能 | 説明 | 技術要素 |
|------|------|----------|
| **F7-1: Metrics収集** | レイテンシ、エラー率、スループット | Cloud Monitoring |
| **F7-2: ログ統合** | 構造化ログの集約 | Cloud Logging |
| **F7-3: トレーシング** | リクエストの分散トレース | Cloud Trace |
| **F7-4: 回答品質評価** | ハルシネーション検出、正確性評価 | Vertex AI Evaluation |
| **F7-5: コスト監視** | トークン使用量、API課金の可視化 | Billing Export + Looker |
| **F7-6: アラート設定** | 異常検知時の通知 | Cloud Alerting |

### ダッシュボード構成
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
- 期間: 2週間
- 工数: 80時間

### ステータス: ⬜ 未着手

---

## Phase 8: 高度機能（InlineViz等） ⬜ 未着手

### 概要
文中描画機能（InlineViz）やその他の高度なUX機能を実装。意思決定支援AIとしての差別化機能を追加。

### 開発理由
- Agent Routerが安定した後に実装すべき機能
- 説明と図の一体化によるユーザー理解度向上
- 競合との差別化要素
- SPEC_inline_viz_future.mdで設計済み

### 機能詳細（SPEC_inline_viz_future.mdより）

#### LLM出力形式（タグベース）
```markdown
売上を分析すると、Q3に大きな伸びが見られます。

<viz type="bar" title="四半期別売上">
{"labels": ["Q1", "Q2", "Q3", "Q4"], "data": [120, 145, 210, 180], "unit": "百万円"}
</viz>

この傾向の要因として、以下の3点が考えられます...
```

#### 対応する描画タイプ
| type | 用途 | レンダラー |
|------|------|-----------|
| bar, line, pie, scatter | データチャート | Plotly |
| flowchart | フローチャート | Mermaid |
| sequence | シーケンス図 | Mermaid |
| table | データテーブル | HTML Table |
| diagram | カスタム図解 | SVG直接描画 |

#### VizTagParser
```python
import re
import json
from dataclasses import dataclass

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
    
    def parse_stream(self, text: str) -> Generator[StreamChunk, None, None]:
        last_end = 0
        for match in self.VIZ_PATTERN.finditer(text):
            if match.start() > last_end:
                yield StreamChunk("text", text[last_end:match.start()])
            
            viz_type, title, data_str = match.groups()
            yield StreamChunk(
                "viz", "",
                {"type": viz_type, "title": title, "data": json.loads(data_str)}
            )
            last_end = match.end()
```

### 開発時間
- 期間: 2週間
- 工数: 80時間

### ステータス: ⬜ 未着手

---

## 依存関係図

```
Phase 0 ──────────────────────────────────────────────────────────────────────────►
    │
    └──► Phase 1: Agent Router ✅ ──────────────────────────────────────────────►
              │
              ├──► Phase 2: Memory Store 🔄 ────────────────────────────────────►
              │         │
              │         └──► Phase 4A: Agent Builder基盤 ───────────────────────►
              │                   │
              │                   └──► Phase 4B: エコシステム連携 ──────────────►
              │                              │
              │                              └──► Phase 5: Enterprise UI ───────►
              │                                         │
              │                                         └──► Phase 6: Governance►
              │                                                    │
              │                                                    └──► Phase 7 ►
              │
              └──► Phase 3: Vertex AI Search ──────────────────────────────────────►
                        │
                        └──► Phase 8: Advanced Features ────────────────────────►
```

### フェーズ依存関係表

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

---

## 開発期間サマリー

| Phase | 名称 | 期間 | 累計 |
|-------|------|------|------|
| 0 | 基盤準備 ✅ | 1週間 | 1週間 |
| 1 | Agent Router ✅ | 1週間 | 2週間 |
| 2 | Memory Store 🔄 | 1週間 | 3週間 |
| 3 | Vertex AI Search | 2週間 | 5週間 |
| 4A | Agent Builder基盤 | 2週間 | 7週間 |
| 4B | エコシステム連携 | 2週間 | 9週間 |
| 5 | Enterprise UI | 3週間 | 12週間 |
| 6 | Governance | 2週間 | 14週間 |
| 7 | Observability | 2週間 | 16週間 |
| 8 | Advanced Features | 2週間 | 18週間 |

**総開発期間: 18週間（約4.5ヶ月）**

---

## リスクと緩和策

| リスク | 影響度 | 緩和策 |
|--------|--------|--------|
| Gemini API仕様変更 | 高 | google-genai SDKの抽象化、バージョン固定 |
| Redis Memorystore障害 | 中 | InMemoryBackendへのフォールバック実装 |
| Agent Builder機能不足 | 中 | LangGraphとのハイブリッド構成維持 |
| Vertex AI Search遅延 | 低 | キャッシュ戦略、バッチ処理 |
| コスト超過 | 中 | FinOps早期導入、Flash優先利用 |
| Claude API クォータ制限 | 中 | Model Routerによるフォールバック |
| A2Aプロトコル仕様変更 | 中 | バージョン固定、抽象化レイヤー |
| 外部エージェント障害 | 低 | タイムアウト設定、ローカルフォールバック |

---

## セキュリティ仕様（継承必須）

| # | 仕様 | 実装箇所 |
|---|------|----------|
| S01 | SQL DML禁止（INSERT/UPDATE/DELETE等13種） | `sql_validator.py` |
| S02 | SELECT/WITH以外の先頭トークン拒否 | `sql_validator.py` |
| S03 | セミコロンによる複文実行防止 | `sql_validator.py` |
| S04 | ファイル名サニタイズ | `domain/models.py` |
| S05 | HTMLエスケープ | インフォグラフィック生成時 |
| S06 | GCSファイルサイズ制限（5MB） | `gcs_service.py` |
| S07 | ファイル拡張子フィルタ | `file_loader.py` |

---

## バージョン管理ルール

```
v{メジャー}.{マイナー}.{パッチ}-{フェーズ}{サフィックス}

例:
- v1.0.0-phase0     # Phase 0完了
- v1.1.0-phase1     # Phase 1完了 ← 現在
- v2.0.0-phase2     # Phase 2完了（次回）
- v4.1.0-stable     # 安定版リリース
```

### 現在のGitタグ
- `v1.1.0-phase1` — Phase 1完了時点

---

## 参考ドキュメント

| ドキュメント | 場所 | 内容 |
|-------------|------|------|
| SPEC_v1.md | /mnt/project/ | 既存コードからの仕様抽出 |
| SPEC_inline_viz_future.md | /mnt/project/ | InlineViz将来設計 |
| PROJECT_STATUS.md | /mnt/project/ | 日次進捗管理 |
| アーキテクチャ概念図 | /mnt/project/*.png | 7層構造図 |

---

## 次回アクション

### Phase 2 タスク
1. [ ] GCP Memorystore for Redis インスタンス作成
2. [ ] RedisMemoryBackend クラス実装
3. [ ] SessionMemoryをBackend抽象化に対応
4. [ ] 環境変数でBackend切替（DI）
5. [ ] 会話履歴の永続化テスト
6. [ ] TTL管理（セッション有効期限）
7. [ ] InMemoryBackend → RedisMemoryBackend 切替確認

### Phase 2 完了基準
- [ ] Redis Memorystore接続成功
- [ ] 会話履歴がセッション間で保持される
- [ ] `git tag v2.0.0-phase2` 作成
- [ ] Streamlit Cloudで動作確認

---

*作成: 2026-03-17*  
*このドキュメントは過去チャット履歴・全プロジェクトファイルを統合した決定版です*
