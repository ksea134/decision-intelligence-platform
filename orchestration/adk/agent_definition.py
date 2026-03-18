"""
orchestration/adk/agent_definition.py — ADKエージェント定義

【役割】
DIPのADKエージェントツリーを定義する。
- root_agent: ルーターエージェント（質問を分類して適切なサブエージェントに委譲）
- analysis_agent: 要因分析エージェント（5 Whys + 寄与度分析）
- comparison_agent: 比較分析エージェント（比較表 + 強み弱み）
- forecast_agent: 予測分析エージェント（3シナリオ）
- general_agent: 汎用回答エージェント

【設計原則】
- 既存のprompt_builder.pyの資産を活用する。
- エージェントごとの専門フレームワークはintent別プロンプトから引き継ぐ。
- ツール（BigQuery, Vertex AI Search）は全エージェントで共有。
"""

from __future__ import annotations

import logging
from google.adk.agents import LlmAgent
from orchestration.adk.tools import query_bigquery, search_past_qa

logger = logging.getLogger(__name__)

# ============================================================
# モデル設定 — エージェントごとに最適なモデルを選択
# ============================================================
MODEL_ROUTER  = "gemini-2.5-flash"   # ルーター: 高速・低コスト（分類のみ）
MODEL_FAST    = "gemini-2.5-flash"   # 汎用回答: 高速・低コスト
MODEL_DEEP    = "gemini-2.5-pro"     # 分析・比較・予測: 高精度・深い推論


# ============================================================
# サブエージェント定義
# ============================================================

analysis_agent = LlmAgent(
    name="analysis_agent",
    model=MODEL_DEEP,
    instruction=(
        "あなたは要因分析の専門家です。\n"
        "ユーザーの質問に対して、以下のフレームワークを適用して回答してください。\n\n"
        "■ 5 Whys（5つのなぜ）:\n"
        "  問題の根本原因に到達するまで「なぜ？」を最低3回繰り返す。\n\n"
        "■ 寄与度分析:\n"
        "  各要因の影響度を%で推定。合計100%になるように配分。\n\n"
        "■ 回答構成:\n"
        "  1. 問題の定義（質問を明確な問題文に再定義）\n"
        "  2. 主要因の特定（寄与度%付き）\n"
        "  3. 根本原因分析（5 Whys）\n"
        "  4. 推奨アクション（短期/中期/長期）\n\n"
        "必要なデータがあれば query_bigquery ツールを使って取得してください。\n"
        "過去の類似分析があれば search_past_qa ツールで検索してください。\n"
    ),
    tools=[query_bigquery, search_past_qa],
)

comparison_agent = LlmAgent(
    name="comparison_agent",
    model=MODEL_DEEP,
    instruction=(
        "あなたは比較分析の専門家です。\n"
        "ユーザーの質問に対して、以下のフレームワークを適用して回答してください。\n\n"
        "■ 比較軸の設定:\n"
        "  定量指標（売上、コスト、成長率等）と定性指標（品質、満足度等）の両面から比較。\n\n"
        "■ 比較表の作成:\n"
        "  3〜5つの主要軸で比較表を作成。差分（+/-）を明記。\n\n"
        "■ 回答構成:\n"
        "  1. 比較対象の定義（表形式）\n"
        "  2. 比較表（数値・差分・優位を含む）\n"
        "  3. 各対象の強み・弱み\n"
        "  4. 総合評価と推奨事項\n\n"
        "必要なデータがあれば query_bigquery ツールを使って取得してください。\n"
        "過去の類似分析があれば search_past_qa ツールで検索してください。\n"
    ),
    tools=[query_bigquery, search_past_qa],
)

forecast_agent = LlmAgent(
    name="forecast_agent",
    model=MODEL_DEEP,
    instruction=(
        "あなたは予測分析の専門家です。\n"
        "ユーザーの質問に対して、以下のフレームワークを適用して回答してください。\n\n"
        "■ 3シナリオ分析:\n"
        "  楽観（15-25%）/ 基本（50-70%）/ 悲観（15-25%）の3パターンで予測。\n\n"
        "■ 予測の根拠:\n"
        "  過去データのトレンド、季節性、外部環境要因を考慮。\n\n"
        "■ 回答構成:\n"
        "  1. 予測の前提条件（期間、対象指標、基準値）\n"
        "  2. シナリオ別予測（表形式: 予測値/成長率/確率）\n"
        "  3. リスク要因と影響度\n"
        "  4. 推奨アクション\n\n"
        "必要なデータがあれば query_bigquery ツールを使って取得してください。\n"
        "過去の類似分析があれば search_past_qa ツールで検索してください。\n"
    ),
    tools=[query_bigquery, search_past_qa],
)

general_agent = LlmAgent(
    name="general_agent",
    model=MODEL_FAST,
    instruction=(
        "あなたは意思決定を支援するトップコンサルタントです。\n"
        "ユーザーの質問に対して、的確で分かりやすい回答を提供してください。\n\n"
        "■ 回答の原則:\n"
        "  1. 結論を先に: 最も重要な回答を冒頭に\n"
        "  2. 根拠を示す: データや事実に基づく説明\n"
        "  3. 詳細を補足: 必要に応じて追加情報\n"
        "  4. 次のステップ: 追加で検討すべき点があれば提示\n\n"
        "必要なデータがあれば query_bigquery ツールを使って取得してください。\n"
        "過去の類似Q&Aがあれば search_past_qa ツールで検索してください。\n"
    ),
    tools=[query_bigquery, search_past_qa],
)


# ============================================================
# ルートエージェント定義
# ============================================================

root_agent = LlmAgent(
    name="dip_root_agent",
    model=MODEL_ROUTER,
    instruction=(
        "あなたはDIP（Decision Intelligence Platform）のルーターエージェントです。\n"
        "ユーザーの質問を分析し、最も適切な専門エージェントに委譲してください。\n\n"
        "## 委譲ルール\n"
        "- 原因・理由・要因を問う質問 → analysis_agent に委譲\n"
        "- 比較・対比・ベンチマークを求める質問 → comparison_agent に委譲\n"
        "- 予測・将来・見通しを問う質問 → forecast_agent に委譲\n"
        "- 上記以外の質問 → general_agent に委譲\n\n"
        "## 重要\n"
        "- あなた自身は回答を生成しないでください。必ずサブエージェントに委譲してください。\n"
        "- 委譲先のエージェントが適切なツール（BigQuery、過去事例検索）を使って回答します。\n"
    ),
    sub_agents=[analysis_agent, comparison_agent, forecast_agent, general_agent],
)


def build_root_agent(
    company: str = "",
    bq_schema: str = "",
    knowledge: str = "",
    prompts: str = "",
) -> LlmAgent:
    """
    企業固有のコンテキストを注入したルートエージェントを構築する。

    実行時に企業名やBQスキーマが分かるため、
    各サブエージェントのinstructionに追加情報を注入する。
    """
    # 企業固有のコンテキストを各サブエージェントに追加
    company_context = ""
    if company:
        company_context += f"\n\n対象企業: {company}\n"
    if bq_schema:
        company_context += f"\nBigQueryスキーマ:\n{bq_schema}\n"
    if knowledge:
        company_context += f"\n企業前提知識:\n{knowledge}\n"
    if prompts:
        company_context += f"\n回答スタイル指示:\n{prompts}\n"

    if company_context:
        for agent in [analysis_agent, comparison_agent, forecast_agent, general_agent]:
            agent.instruction = agent.instruction + company_context

    return root_agent
