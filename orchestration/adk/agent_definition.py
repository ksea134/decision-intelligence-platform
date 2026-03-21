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
from orchestration.adk.tools import query_bigquery

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
        "データが必要な場合は query_bigquery ツールを呼んでください。全テーブルのデータがCSVで返されます。\n"
    ),
    tools=[query_bigquery],
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
        "データが必要な場合は query_bigquery ツールを呼んでください。全テーブルのデータがCSVで返されます。\n"
    ),
    tools=[query_bigquery],
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
        "データが必要な場合は query_bigquery ツールを呼んでください。全テーブルのデータがCSVで返されます。\n"
    ),
    tools=[query_bigquery],
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
        "データが必要な場合は query_bigquery ツールを呼んでください。全テーブルのデータがCSVで返されます。\n"
    ),
    tools=[query_bigquery],
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


# 各エージェントの元のinstructionを保存（毎回リセットするため）
_BASE_INSTRUCTIONS = {
    "analysis_agent": analysis_agent.instruction,
    "comparison_agent": comparison_agent.instruction,
    "forecast_agent": forecast_agent.instruction,
    "general_agent": general_agent.instruction,
}


def build_root_agent(
    company: str = "",
    bq_schema: str = "",
    gcs_docs: str = "",
    knowledge: str = "",
    prompts: str = "",
    past_qa_context: str = "",
) -> LlmAgent:
    """
    企業固有のコンテキストを注入したルートエージェントを構築する。

    実行時に企業名やBQスキーマが分かるため、
    各サブエージェントのinstructionに追加情報を注入する。
    注意: 毎回ベースinstructionからリセットしてから追記する（累積防止）。
    """
    # 企業固有のコンテキストを組み立て
    company_context = ""
    if company:
        company_context += f"\n\n対象企業: {company}\n"
    if bq_schema:
        safe_bq_schema = bq_schema.replace("{", "｛").replace("}", "｝") if isinstance(bq_schema, str) else str(bq_schema).replace("{", "｛").replace("}", "｝")
        company_context += f"\nBigQueryスキーマ:\n{safe_bq_schema}\n"
    if gcs_docs:
        # ADKがinstruction内の{...}をテンプレート変数と誤認するため、波括弧を全角に変換
        safe_gcs_docs = gcs_docs.replace("{", "｛").replace("}", "｝")
        company_context += (
            "\n【GCS資料（報告書・分析レポート — 必ず回答に反映すること）】\n"
            "※以下の資料には数値の背景・原因・考察が含まれている。\n"
            "※数値データ（BigQuery）と合わせて、資料の内容も必ず踏まえて回答すること。\n"
            "※数値だけの回答は不十分。資料に書かれた背景・要因・提言も含めること。\n"
            f"{safe_gcs_docs}\n"
        )
    if past_qa_context:
        safe_past_qa = past_qa_context.replace("{", "｛").replace("}", "｝")
        company_context += (
            "\n【過去の類似Q&A — 参考にして回答の一貫性を保つこと】\n"
            f"{safe_past_qa}\n"
        )
    if knowledge:
        safe_knowledge = knowledge.replace("{", "｛").replace("}", "｝")
        company_context += f"\n企業前提知識:\n{safe_knowledge}\n"
    if prompts:
        safe_prompts = prompts.replace("{", "｛").replace("}", "｝")
        company_context += f"\n回答スタイル指示:\n{safe_prompts}\n"

    # 出典情報の記載ルール（全エージェント共通）
    company_context += (
        "\n\n【出典情報の記載ルール（必須）】\n"
        "回答本文中でデータを参照した箇所に※1、※2のような米印番号を付けること。\n"
        "回答末尾に米印番号と参照したデータソース名の対応一覧を記載すること。\n"
        "実際に回答の根拠として使ったデータのみ記載（使っていないデータは書かない）。\n"
        "例: ※1：BQ:production_results  ※2：GCS:inspection_report.txt\n"
        "データソース名の形式: BQ:テーブル名 / GCS:ファイル名 / LOCAL:ファイル名\n"
        "\n\n【チャート描画タグ（任意）】\n"
        "数値データをチャートで可視化すると理解が深まる箇所には、以下の形式で <viz> タグを挿入:\n"
        '<viz type="bar" title="タイトル">\n'
        '｛"labels": ["A","B","C"], "data": [100,200,150]｝\n'
        "</viz>\n"
        '使えるtype: "bar"（比較）, "line"（推移）, "pie"（構成比）。最大3つまで。不要なら使わない。\n'
    )

    # ベースinstructionにリセットしてから企業コンテキストを追加（累積防止）
    for agent in [analysis_agent, comparison_agent, forecast_agent, general_agent]:
        agent.instruction = _BASE_INSTRUCTIONS[agent.name] + company_context

    return root_agent
