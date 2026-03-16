"""
orchestration/graph/state.py — LangGraph 状態定義

【役割】
ワークフロー全体で共有される状態（State）を定義する。
各ノード（意図分類、要因分析、比較など）はこの状態を読み書きする。

【設計原則】
- TypedDict を使用し、型安全性を確保
- 不変データ（入力）と可変データ（中間結果）を明確に分離
- 将来の拡張に備えてオプショナルフィールドを用意
"""
from __future__ import annotations

from typing import Any, Literal, TypedDict


# -----------------------------------------------------------------------------
# 意図の種類（Router が決定する）
# -----------------------------------------------------------------------------
IntentType = Literal["analysis", "comparison", "forecast", "general"]


# -----------------------------------------------------------------------------
# 分類結果
# -----------------------------------------------------------------------------
class ClassificationResult(TypedDict, total=False):
    """Router Agent が出力する分類結果"""
    intent: IntentType
    confidence: float  # 0.0 〜 1.0
    reasoning: str  # 分類理由の簡潔な説明
    entities: list[str]  # 抽出したキーワード


# -----------------------------------------------------------------------------
# エージェント実行結果
# -----------------------------------------------------------------------------
class AgentResult(TypedDict, total=False):
    """各エージェントが出力する実行結果"""
    response_text: str  # LLM の生成テキスト
    files: list[str]  # 参照したファイル [FILES: ...] タグから抽出
    sql_query: str | None  # 実行した SQL
    sql_result: dict[str, Any] | None  # SQL 実行結果
    structured_data: dict[str, Any] | None  # 構造化された分析結果（要因分析の寄与度など）
    chart_config: dict[str, Any] | None  # チャート設定（将来用）


# -----------------------------------------------------------------------------
# ワークフロー全体の状態
# -----------------------------------------------------------------------------
class WorkflowState(TypedDict, total=False):
    """
    LangGraph ワークフローの状態。
    
    各ノードはこの状態を読み取り、必要なフィールドを更新する。
    LangGraph は状態の差分を自動的にマージする。
    
    【フィールド説明】
    
    入力（不変）:
    - user_prompt: ユーザーの質問テキスト
    - display_label: UI に表示するラベル（スマートカードの場合は異なる）
    - company: 選択中の企業名
    - company_folder: 企業のデータフォルダ名
    
    コンテキスト（外部から注入）:
    - bq_schema: BigQuery スキーマ情報
    - gcs_docs: GCS ドキュメント内容
    - knowledge: 企業別前提知識
    - prompts: 回答スタイル定義
    - structured_data: ローカル構造化データ
    - unstructured_data: ローカル非構造化データ
    - bq_connected: BigQuery 接続状態
    
    中間結果（各ノードが更新）:
    - classification: Router の分類結果
    - current_agent: 現在実行中のエージェント名
    - agent_result: エージェントの実行結果
    
    最終出力:
    - final_response: 最終的な回答テキスト
    - thought_process: 思考ロジック（4ステップ）
    - infographic_html: インフォグラフィック HTML
    - infographic_data: インフォグラフィック JSON データ
    - deep_dive_questions: 深掘り質問リスト
    
    メタデータ:
    - error: エラーメッセージ（あれば）
    - execution_time_ms: 実行時間（ミリ秒）
    """
    
    # --- 入力（不変） ---
    user_prompt: str
    display_label: str
    company: str
    company_folder: str
    
    # --- コンテキスト（外部から注入） ---
    bq_schema: str
    gcs_docs: str
    knowledge: str
    prompts: str
    structured_data: str
    unstructured_data: str
    bq_connected: bool
    
    # --- 中間結果 ---
    classification: ClassificationResult
    current_agent: str
    agent_result: AgentResult
    
    # --- 最終出力 ---
    final_response: str
    thought_process: str
    infographic_html: str
    infographic_data: dict[str, Any]
    deep_dive_questions: list[str]
    
    # --- メタデータ ---
    error: str | None
    execution_time_ms: float


# -----------------------------------------------------------------------------
# 状態の初期化ヘルパー
# -----------------------------------------------------------------------------
def create_initial_state(
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
) -> WorkflowState:
    """
    ワークフロー状態の初期値を生成する。
    
    Args:
        user_prompt: ユーザーの質問
        display_label: 表示用ラベル
        company: 企業名
        company_folder: 企業フォルダ名
        その他: コンテキスト情報
    
    Returns:
        初期化された WorkflowState
    """
    return WorkflowState(
        # 入力
        user_prompt=user_prompt,
        display_label=display_label,
        company=company,
        company_folder=company_folder,
        # コンテキスト
        bq_schema=bq_schema,
        gcs_docs=gcs_docs,
        knowledge=knowledge,
        prompts=prompts,
        structured_data=structured_data,
        unstructured_data=unstructured_data,
        bq_connected=bq_connected,
        # 中間結果（空で初期化）
        classification=ClassificationResult(),
        current_agent="",
        agent_result=AgentResult(),
        # 最終出力（空で初期化）
        final_response="",
        thought_process="",
        infographic_html="",
        infographic_data={},
        deep_dive_questions=[],
        # メタデータ
        error=None,
        execution_time_ms=0.0,
    )
