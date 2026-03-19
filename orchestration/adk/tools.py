"""
orchestration/adk/tools.py — ADK用ツール定義

【役割】
ADKエージェントが使用するツール（BigQuery検索、Vertex AI Search）を定義する。
既存のインフラ層（data_agent, vertex_ai_search）をラップして、
ADKのFunctionTool形式で提供する。

【設計原則】
- 既存コードをラップするだけ。新しいロジックは追加しない。
- ツール内でエラーを処理し、エラーメッセージを返す（例外は投げない）。
- SQLバリデーション（auto_backtick_japanese）を必ず通す。
"""

from __future__ import annotations

import logging
import re
from typing import Any


logger = logging.getLogger(__name__)

# グローバル参照（runner.py から設定される）
_data_agent = None
_search_client = None
_data_ctx = None
_company = None
_last_search_result_count = 0
_last_bq_tables: list[str] = []


def set_tool_context(data_agent, search_client, data_ctx, company: str) -> None:
    """ツールが参照するコンテキストを設定する。各リクエストの開始時に呼ぶ。"""
    global _data_agent, _search_client, _data_ctx, _company
    _data_agent = data_agent
    _search_client = search_client
    _data_ctx = data_ctx
    _company = company


def query_bigquery() -> str:
    """
    BigQueryから全テーブルのデータを取得する。

    SELECT * LIMIT 100 で全テーブルを取得し、CSV形式で返す。
    SQL生成はGeminiに任せず、固定SQLで確実にデータを取得する（開発ルールC03）。

    Returns:
        CSV形式のデータ、またはエラーメッセージ。
    """
    if _data_agent is None:
        return "Error: BigQuery is not configured."
    if _data_ctx is None:
        return "Error: No data context available."

    global _last_bq_tables
    logger.warning("[ADK Tool] query_bigquery called: SELECT * 固定方式")
    _last_bq_tables = []

    try:
        schema_text = _data_ctx.bq_result.content
        tables = re.findall(r"Dataset:\s*(\S+)[\s\S]*?Table:\s*(\S+)", schema_text)
        if not tables:
            return "Error: No tables found in schema."

        all_parts = []
        for dataset, table in tables:
            _last_bq_tables.append(table)
            sql = f"SELECT * FROM `{dataset}`.`{table}` LIMIT 100"
            try:
                result = _data_agent.execute_sql(sql)
                if result and result.row_count > 0:
                    df = result.to_dataframe()
                    all_parts.append(f"--- {dataset}.{table} ---\n{df.head(100).to_csv(index=False)}")
                    logger.warning("[ADK Tool] %s.%s: %d行取得", dataset, table, result.row_count)
            except Exception as e:
                logger.error("[ADK Tool] %s.%s 取得エラー: %s", dataset, table, e)

        if not all_parts:
            return "Error: Could not retrieve any data."

        return "\n\n".join(all_parts)
    except Exception as e:
        logger.error("[ADK Tool] query_bigquery error: %s", e)
        return f"Error: {e}"


def search_past_qa(query: str) -> str:
    """
    過去の類似Q&Aを検索する。

    Args:
        query: 検索クエリ（ユーザーの質問文）。

    Returns:
        過去の類似Q&Aのテキスト、または「類似事例なし」。
    """
    if _search_client is None or not _search_client.is_ready():
        return "過去事例検索は利用できません。"

    global _last_search_result_count
    try:
        logger.warning("[ADK Tool] search_past_qa called: query='%s', _company='%s'", query[:50], _company)
        results = _search_client.search(query=query, company=_company or "", top_k=3)
        _last_search_result_count = len(results)
        if not results:
            return "類似する過去の事例は見つかりませんでした。"

        parts = []
        for i, qa in enumerate(results, 1):
            parts.append(
                f"事例{i}:\n"
                f"  質問: {qa.get('question', '')}\n"
                f"  回答: {qa.get('answer', '')}"
            )
        return "\n\n".join(parts)
    except Exception as e:
        logger.error("[ADK Tool] search_past_qa error: %s", e)
        return "過去事例の検索中にエラーが発生しました。"


