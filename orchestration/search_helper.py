"""
orchestration/search_helper.py — 過去事例検索ヘルパー（V1/ADK共通）

V1エンジンとADKエンジンで重複していた過去事例検索処理を統一。
片方を修正してもう片方を忘れる問題を解消する。
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def search_past_qa(
    search_client: Any,
    user_prompt: str,
    company: str,
    trace: Any = None,
) -> tuple[str, str, int]:
    """過去事例を検索し、コンテキスト文字列を返す。

    Args:
        search_client: Vertex AI Searchクライアント（Noneの場合はスキップ）
        user_prompt: ユーザーの質問文
        company: 企業名
        trace: RequestTraceオブジェクト（計測用、Noneの場合はスキップ）

    Returns:
        (past_qa_context, detail_message, result_count)
        - past_qa_context: プロンプトに注入するコンテキスト文字列
        - detail_message: フロー表示用の詳細メッセージ
        - result_count: 検出された類似事例数
    """
    if trace:
        trace.begin_step("past_qa_search")

    if not search_client or not search_client.is_ready():
        if trace:
            trace.end_step("未接続")
        return "", "未接続", 0

    try:
        similar_qas = search_client.search(query=user_prompt, company=company, top_k=3)
        if similar_qas:
            parts = []
            for i, qa in enumerate(similar_qas, 1):
                parts.append(f"事例{i}:\n  質問: {qa.get('question', '')}\n  回答: {qa.get('answer', '')}")
            context = "\n\n".join(parts)
            detail = f"{len(similar_qas)}件の類似事例を発見"
            if trace:
                trace.end_step(f"{len(similar_qas)}件の類似事例")
            logger.info("[Search] %d similar Q&As found", len(similar_qas))
            return context, detail, len(similar_qas)
        else:
            if trace:
                trace.end_step("類似事例なし")
            return "", "類似事例なし", 0

    except Exception as e:
        logger.warning("[Search] Failed: %s", e)
        if trace:
            trace.end_step(f"エラー: {e}", status="error")
        return "", "検索スキップ", 0
