"""
orchestration/graph/workflow.py — LangGraph ワークフロー定義

【役割】
Agent Router のメインワークフローを定義する。
ユーザーの質問 → 意図分類 → 適切なエージェント → 出力整形 の流れを制御。

【設計原則】
- LangGraph の StateGraph を使用
- 各ノードは純粋関数として実装（副作用なし）
- エラーハンドリングは各ノード内で完結
- Gemini API 呼び出しは外部から注入（テスト容易性）

【ノード構成】
START → classify_intent → (条件分岐) → [analysis|comparison|forecast|general] → format_response → END

【修正履歴】
- 2026-03-16: Step 2 - RouterAgent を使用した LLM ベースの意図分類を追加
- 2026-03-16: google-genai をオプションインポートに変更（テスト環境対応）
"""
from __future__ import annotations

import logging
import time
from typing import Any, Callable, Optional, TYPE_CHECKING

from langgraph.graph import END, START, StateGraph

from orchestration.graph.state import (
    AgentResult,
    ClassificationResult,
    IntentType,
    WorkflowState,
)

# google-genai はオプション依存（テスト環境では不要）
try:
    from google import genai
    GENAI_AVAILABLE = True
except ImportError:
    genai = None  # type: ignore
    GENAI_AVAILABLE = False

# RouterAgent は google-genai に依存するため、遅延インポート
if TYPE_CHECKING:
    from orchestration.agents.router_agent import RouterAgent

logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# ノード関数の型定義
# -----------------------------------------------------------------------------
# 各ノードは WorkflowState を受け取り、更新する部分のみを dict で返す
NodeFunction = Callable[[WorkflowState], dict[str, Any]]


# -----------------------------------------------------------------------------
# ノード: 意図分類（Router）— キーワードベース（フォールバック用）
# -----------------------------------------------------------------------------
def classify_intent_keyword(state: WorkflowState) -> dict[str, Any]:
    """
    キーワードベースでユーザーの質問を分類する（フォールバック用）。
    
    【分類ルール】
    - analysis: 「なぜ」「原因」「理由」「要因」を含む
    - comparison: 「比較」「違い」「vs」「どちらが」を含む
    - forecast: 「予測」「今後」「見通し」「どうなる」を含む
    - general: 上記以外
    """
    user_prompt = state.get("user_prompt", "").lower()
    
    # キーワードベースの簡易分類
    analysis_keywords = ["なぜ", "原因", "理由", "要因", "どうして", "why"]
    comparison_keywords = ["比較", "違い", "差", "vs", "どちらが", "compare", "より"]
    forecast_keywords = ["予測", "今後", "見通し", "どうなる", "将来", "forecast", "来月", "来年"]
    
    intent: IntentType = "general"
    confidence = 0.5
    reasoning = "特定のパターンに該当しないため汎用エージェントを選択"
    entities: list[str] = []
    
    # キーワードマッチング
    if any(kw in user_prompt for kw in analysis_keywords):
        intent = "analysis"
        confidence = 0.75
        reasoning = "キーワードベース: 原因・理由を問う質問パターンを検出"
        entities = [kw for kw in analysis_keywords if kw in user_prompt]
    elif any(kw in user_prompt for kw in comparison_keywords):
        intent = "comparison"
        confidence = 0.75
        reasoning = "キーワードベース: 比較を求める質問パターンを検出"
        entities = [kw for kw in comparison_keywords if kw in user_prompt]
    elif any(kw in user_prompt for kw in forecast_keywords):
        intent = "forecast"
        confidence = 0.75
        reasoning = "キーワードベース: 予測・将来を問う質問パターンを検出"
        entities = [kw for kw in forecast_keywords if kw in user_prompt]
    
    classification = ClassificationResult(
        intent=intent,
        confidence=confidence,
        reasoning=reasoning,
        entities=entities,
    )
    
    logger.info(
        "[Router/Keyword] intent=%s, confidence=%.2f, reasoning=%s",
        intent, confidence, reasoning
    )
    
    return {
        "classification": classification,
        "current_agent": f"{intent}_agent",
    }


# 後方互換性のためのエイリアス
classify_intent = classify_intent_keyword


# -----------------------------------------------------------------------------
# ノードファクトリ: 意図分類（Router）— LLM ベース
# -----------------------------------------------------------------------------
def create_classify_intent_node(router_agent: "RouterAgent") -> NodeFunction:
    """
    LLM ベースの意図分類ノードを生成するファクトリ関数。
    
    Args:
        router_agent: RouterAgent インスタンス
    
    Returns:
        ノード関数（WorkflowState → dict）
    """
    def classify_intent_llm(state: WorkflowState) -> dict[str, Any]:
        """
        LLM（Gemini Flash）を使用してユーザーの質問を分類する。
        """
        user_prompt = state.get("user_prompt", "")
        
        # RouterAgent で分類
        classification = router_agent.classify(user_prompt)
        
        logger.info(
            "[Router/LLM] intent=%s, confidence=%.2f, reasoning=%s",
            classification.get("intent"),
            classification.get("confidence"),
            classification.get("reasoning"),
        )
        
        return {
            "classification": classification,
            "current_agent": f"{classification.get('intent', 'general')}_agent",
        }
    
    return classify_intent_llm


# -----------------------------------------------------------------------------
# ノード: 要因分析エージェント
# -----------------------------------------------------------------------------
def run_analysis_agent(state: WorkflowState) -> dict[str, Any]:
    """
    要因分析エージェントを実行する。
    
    【処理内容】
    1. データ収集（BQ/GCS/ローカル）
    2. 要因分解（フレームワーク適用）
    3. 深掘り分析
    4. 構造化出力
    
    【注意】
    本番実装では Gemini Pro を使用して分析を行う。
    ここではスタブ実装としている。
    """
    user_prompt = state.get("user_prompt", "")
    company = state.get("company", "")
    
    logger.info("[AnalysisAgent] Processing: %s", user_prompt[:50])
    
    # スタブ実装（本番では Gemini Pro 呼び出し）
    response_text = f"""
## 要因分析結果

**質問**: {user_prompt}

### 主要因の特定
分析フレームワークを適用し、以下の要因を特定しました。

1. **主要因A** (寄与度: 60%)
   - 詳細な説明...

2. **副次要因B** (寄与度: 25%)
   - 詳細な説明...

3. **その他要因** (寄与度: 15%)
   - 詳細な説明...

### 根本原因
5 Whys 分析の結果、根本原因は...

### 推奨アクション
1. アクションA
2. アクションB

[FILES: analysis_framework.md, company_data.csv]
"""
    
    agent_result = AgentResult(
        response_text=response_text,
        files=["analysis_framework.md", "company_data.csv"],
        sql_query=None,
        sql_result=None,
        structured_data={
            "primary_cause": {"factor": "主要因A", "contribution": 60},
            "secondary_causes": [
                {"factor": "副次要因B", "contribution": 25},
                {"factor": "その他", "contribution": 15},
            ],
        },
    )
    
    return {"agent_result": agent_result}


# -----------------------------------------------------------------------------
# ノード: 比較エージェント
# -----------------------------------------------------------------------------
def run_comparison_agent(state: WorkflowState) -> dict[str, Any]:
    """
    比較エージェントを実行する。
    
    【処理内容】
    1. 比較対象の特定
    2. 比較軸の決定
    3. データ取得・計算
    4. 構造化出力（比較表）
    """
    user_prompt = state.get("user_prompt", "")
    
    logger.info("[ComparisonAgent] Processing: %s", user_prompt[:50])
    
    # スタブ実装
    response_text = f"""
## 比較分析結果

**質問**: {user_prompt}

### 比較サマリー
| 項目 | 対象A | 対象B | 差分 |
|------|-------|-------|------|
| 売上 | ¥100M | ¥80M | +25% |
| 利益率 | 15% | 18% | -3pt |
| 成長率 | +8% | +12% | -4pt |

### 結論
対象Aは規模で優位、対象Bは収益性・成長性で優位です。

[FILES: comparison_data.csv]
"""
    
    agent_result = AgentResult(
        response_text=response_text,
        files=["comparison_data.csv"],
        structured_data={
            "comparison_type": "対象比較",
            "targets": ["対象A", "対象B"],
        },
    )
    
    return {"agent_result": agent_result}


# -----------------------------------------------------------------------------
# ノード: 予測エージェント
# -----------------------------------------------------------------------------
def run_forecast_agent(state: WorkflowState) -> dict[str, Any]:
    """
    予測エージェントを実行する。
    
    【処理内容】
    1. 過去データ収集
    2. パターン分析
    3. シナリオ生成（楽観/基本/悲観）
    4. 構造化出力
    """
    user_prompt = state.get("user_prompt", "")
    
    logger.info("[ForecastAgent] Processing: %s", user_prompt[:50])
    
    # スタブ実装
    response_text = f"""
## 予測分析結果

**質問**: {user_prompt}

### シナリオ別予測
| シナリオ | 予測値 | 確率 |
|----------|--------|------|
| 楽観 | ¥110M | 25% |
| 基本 | ¥95M | 60% |
| 悲観 | ¥85M | 15% |

### 予測根拠
- 過去12ヶ月のトレンド分析に基づく
- 季節性を考慮

### リスク要因
- 競合の動向
- 市場環境の変化

[FILES: historical_data.csv, forecast_model.md]
"""
    
    agent_result = AgentResult(
        response_text=response_text,
        files=["historical_data.csv", "forecast_model.md"],
        structured_data={
            "scenarios": {
                "optimistic": {"value": 110, "probability": 0.25},
                "base": {"value": 95, "probability": 0.60},
                "pessimistic": {"value": 85, "probability": 0.15},
            },
        },
    )
    
    return {"agent_result": agent_result}


# -----------------------------------------------------------------------------
# ノード: 汎用エージェント
# -----------------------------------------------------------------------------
def run_general_agent(state: WorkflowState) -> dict[str, Any]:
    """
    汎用エージェントを実行する（スタブ実装）。
    
    【処理内容】
    現行の ReasoningEngine と同等の処理を行う。
    特定の分析パターンに該当しない質問に対応。
    """
    user_prompt = state.get("user_prompt", "")
    
    logger.info("[GeneralAgent/Stub] Processing: %s", user_prompt[:50])
    
    # スタブ実装（本番では既存の ReasoningEngine を呼び出し）
    response_text = f"""
## 回答

**質問**: {user_prompt}

ご質問にお答えします。

（ここに汎用的な回答が入ります）

詳細についてはお気軽にお尋ねください。

[FILES: knowledge_base.md]
"""
    
    agent_result = AgentResult(
        response_text=response_text,
        files=["knowledge_base.md"],
    )
    
    return {"agent_result": agent_result}


# -----------------------------------------------------------------------------
# ノードファクトリ: 各エージェント（LLM ベース）
# -----------------------------------------------------------------------------
def create_analysis_agent_node(client: Any) -> NodeFunction:
    """
    LLM ベースの要因分析エージェントノードを生成する。
    
    Args:
        client: Gemini API クライアント
    
    Returns:
        ノード関数
    """
    from orchestration.agents.analysis_agent import AnalysisAgent
    agent = AnalysisAgent(client=client)
    
    def run_analysis_agent_llm(state: WorkflowState) -> dict[str, Any]:
        return agent.run(state)
    
    return run_analysis_agent_llm


def create_comparison_agent_node(client: Any) -> NodeFunction:
    """
    LLM ベースの比較エージェントノードを生成する。
    
    Args:
        client: Gemini API クライアント
    
    Returns:
        ノード関数
    """
    from orchestration.agents.comparison_agent import ComparisonAgent
    agent = ComparisonAgent(client=client)
    
    def run_comparison_agent_llm(state: WorkflowState) -> dict[str, Any]:
        return agent.run(state)
    
    return run_comparison_agent_llm


def create_forecast_agent_node(client: Any) -> NodeFunction:
    """
    LLM ベースの予測エージェントノードを生成する。
    
    Args:
        client: Gemini API クライアント
    
    Returns:
        ノード関数
    """
    from orchestration.agents.forecast_agent import ForecastAgent
    agent = ForecastAgent(client=client)
    
    def run_forecast_agent_llm(state: WorkflowState) -> dict[str, Any]:
        return agent.run(state)
    
    return run_forecast_agent_llm


def create_general_agent_node(client: Any) -> NodeFunction:
    """
    LLM ベースの汎用エージェントノードを生成する。
    
    Args:
        client: Gemini API クライアント
    
    Returns:
        ノード関数
    """
    from orchestration.agents.general_agent import GeneralAgent
    agent = GeneralAgent(client=client)
    
    def run_general_agent_llm(state: WorkflowState) -> dict[str, Any]:
        return agent.run(state)
    
    return run_general_agent_llm


# -----------------------------------------------------------------------------
# ノード: 出力整形
# -----------------------------------------------------------------------------
def format_response(state: WorkflowState) -> dict[str, Any]:
    """
    エージェントの出力を最終形式に整形する。
    
    【処理内容】
    1. agent_result から final_response を生成
    2. 思考ロジック生成（本番では別途 LLM 呼び出し）
    3. インフォグラフィック生成（本番では別途 LLM 呼び出し）
    4. 深掘り質問生成（本番では別途 LLM 呼び出し）
    """
    agent_result = state.get("agent_result", {})
    classification = state.get("classification", {})
    
    response_text = agent_result.get("response_text", "")
    intent = classification.get("intent", "general")
    
    logger.info("[FormatResponse] Formatting output for intent=%s", intent)
    
    # 思考ロジック生成（スタブ）
    thought_process = f"""
### Step 1: データの定量的把握
質問を受け、関連するデータを収集しました。

### Step 2: リスク・文脈の把握
{intent} タイプの質問として分析を行いました。

### Step 3: 論点・仮説の統合
複数の観点から検討し、仮説を統合しました。

### Step 4: 回答方針
上記の分析に基づき、回答を構成しました。
"""
    
    # 深掘り質問生成（スタブ）
    deep_dive_questions = [
        "この結果についてさらに詳しく知りたい点はありますか？",
        "他の観点からの分析も見てみますか？",
        "関連するデータを確認しますか？",
    ]
    
    return {
        "final_response": response_text,
        "thought_process": thought_process,
        "deep_dive_questions": deep_dive_questions,
    }


# -----------------------------------------------------------------------------
# 条件分岐関数
# -----------------------------------------------------------------------------
def route_by_intent(state: WorkflowState) -> str:
    """
    分類結果に基づいて次のノードを決定する。
    
    Returns:
        次に実行するノード名
    """
    classification = state.get("classification", {})
    intent = classification.get("intent", "general")
    confidence = classification.get("confidence", 0.0)
    
    # 信頼度が低い場合は汎用エージェントにフォールバック
    if confidence < 0.7:
        logger.info("[Router] Low confidence (%.2f), falling back to general", confidence)
        return "general_agent"
    
    # 意図に基づいてルーティング
    route_map = {
        "analysis": "analysis_agent",
        "comparison": "comparison_agent",
        "forecast": "forecast_agent",
        "general": "general_agent",
    }
    
    return route_map.get(intent, "general_agent")


# -----------------------------------------------------------------------------
# ワークフロー構築
# -----------------------------------------------------------------------------
def build_workflow(
    client: Optional[Any] = None,
    use_llm_router: bool = True,
    use_llm_agents: bool = True,
) -> StateGraph:
    """
    Agent Router ワークフローを構築する。
    
    【グラフ構造】
    START
      ↓
    classify_intent（意図分類）
      ↓
    (条件分岐: route_by_intent)
      ├→ analysis_agent（要因分析）
      ├→ comparison_agent（比較）
      ├→ forecast_agent（予測）
      └→ general_agent（汎用）
           ↓
    format_response（出力整形）
      ↓
    END
    
    Args:
        client: Gemini API クライアント（LLM を使用する場合）
        use_llm_router: LLM ベースの Router を使用するか（デフォルト: True）
                       False の場合はキーワードベースの分類を使用
        use_llm_agents: LLM ベースのエージェントを使用するか（デフォルト: True）
                       False の場合はスタブ実装を使用
    
    Returns:
        StateGraph オブジェクト
    """
    # グラフの初期化
    workflow = StateGraph(WorkflowState)
    
    # Router ノードの選択
    if use_llm_router and client is not None:
        # LLM ベースの Router を使用（遅延インポート）
        from orchestration.agents.router_agent import RouterAgent
        router_agent = RouterAgent(client=client)
        classify_node = create_classify_intent_node(router_agent)
        logger.info("[Workflow] Using LLM-based Router (Gemini Flash)")
    else:
        # キーワードベースの Router を使用（フォールバック）
        classify_node = classify_intent_keyword
        if use_llm_router and client is None:
            logger.warning(
                "[Workflow] LLM Router requested but no client provided, "
                "falling back to keyword-based Router"
            )
        else:
            logger.info("[Workflow] Using keyword-based Router")
    
    # エージェントノードの選択
    if use_llm_agents and client is not None:
        # LLM ベースのエージェントを使用
        analysis_node = create_analysis_agent_node(client)
        comparison_node = create_comparison_agent_node(client)
        forecast_node = create_forecast_agent_node(client)
        general_node = create_general_agent_node(client)
        logger.info("[Workflow] Using LLM-based Agents (Gemini Pro)")
    else:
        # スタブ実装を使用（フォールバック）
        analysis_node = run_analysis_agent
        comparison_node = run_comparison_agent
        forecast_node = run_forecast_agent
        general_node = run_general_agent
        if use_llm_agents and client is None:
            logger.warning(
                "[Workflow] LLM Agents requested but no client provided, "
                "falling back to stub implementations"
            )
        else:
            logger.info("[Workflow] Using stub Agents")
    
    # ノードの追加
    workflow.add_node("classify_intent", classify_node)
    workflow.add_node("analysis_agent", analysis_node)
    workflow.add_node("comparison_agent", comparison_node)
    workflow.add_node("forecast_agent", forecast_node)
    workflow.add_node("general_agent", general_node)
    workflow.add_node("format_response", format_response)
    
    # エッジの追加
    # START → classify_intent
    workflow.add_edge(START, "classify_intent")
    
    # classify_intent → (条件分岐)
    workflow.add_conditional_edges(
        "classify_intent",
        route_by_intent,
        {
            "analysis_agent": "analysis_agent",
            "comparison_agent": "comparison_agent",
            "forecast_agent": "forecast_agent",
            "general_agent": "general_agent",
        },
    )
    
    # 各エージェント → format_response
    workflow.add_edge("analysis_agent", "format_response")
    workflow.add_edge("comparison_agent", "format_response")
    workflow.add_edge("forecast_agent", "format_response")
    workflow.add_edge("general_agent", "format_response")
    
    # format_response → END
    workflow.add_edge("format_response", END)
    
    return workflow


def compile_workflow(
    client: Optional[Any] = None,
    use_llm_router: bool = True,
    use_llm_agents: bool = True,
):
    """
    ワークフローをコンパイルして実行可能な形式にする。
    
    Args:
        client: Gemini API クライアント（LLM を使用する場合）
        use_llm_router: LLM ベースの Router を使用するか（デフォルト: True）
        use_llm_agents: LLM ベースのエージェントを使用するか（デフォルト: True）
    
    Returns:
        コンパイル済みのワークフロー
    """
    workflow = build_workflow(
        client=client,
        use_llm_router=use_llm_router,
        use_llm_agents=use_llm_agents,
    )
    return workflow.compile()


# -----------------------------------------------------------------------------
# 実行ヘルパー
# -----------------------------------------------------------------------------
def run_workflow(
    user_prompt: str,
    display_label: str,
    company: str,
    company_folder: str,
    bq_schema: str = "",
    gcs_docs: str = "",
    knowledge: str = "",
    prompts: str = "",
    structured_data: str = "",
    unstructured_data: str = "",
    bq_connected: bool = False,
    client: Optional[Any] = None,
    use_llm_router: bool = True,
    use_llm_agents: bool = True,
) -> WorkflowState:
    """
    ワークフローを実行する。
    
    Args:
        user_prompt: ユーザーの質問
        display_label: 表示用ラベル
        company: 企業名
        company_folder: 企業フォルダ名
        bq_schema: BigQuery スキーマ
        gcs_docs: GCS ドキュメント
        knowledge: 企業別前提知識
        prompts: 回答スタイル定義
        structured_data: ローカル構造化データ
        unstructured_data: ローカル非構造化データ
        bq_connected: BigQuery 接続状態
        client: Gemini API クライアント（LLM を使用する場合）
        use_llm_router: LLM ベースの Router を使用するか（デフォルト: True）
        use_llm_agents: LLM ベースのエージェントを使用するか（デフォルト: True）
    
    Returns:
        実行後の WorkflowState
    """
    from orchestration.graph.state import create_initial_state
    
    start_time = time.time()
    
    # 初期状態を作成
    initial_state = create_initial_state(
        user_prompt=user_prompt,
        display_label=display_label,
        company=company,
        company_folder=company_folder,
        bq_schema=bq_schema,
        gcs_docs=gcs_docs,
        knowledge=knowledge,
        prompts=prompts,
        structured_data=structured_data,
        unstructured_data=unstructured_data,
        bq_connected=bq_connected,
    )
    
    # ワークフローをコンパイル
    app = compile_workflow(
        client=client,
        use_llm_router=use_llm_router,
        use_llm_agents=use_llm_agents,
    )
    
    # 実行
    result = app.invoke(initial_state)
    
    # 実行時間を記録
    execution_time_ms = (time.time() - start_time) * 1000
    result["execution_time_ms"] = execution_time_ms
    
    logger.info("[Workflow] Completed in %.2f ms", execution_time_ms)
    
    return result
