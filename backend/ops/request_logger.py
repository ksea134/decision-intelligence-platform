"""
backend/ops/request_logger.py — リクエストログ記録

各チャットリクエストの詳細を構造化ログとして記録する。
Cloud Run環境ではCloud Logging→BigQueryシンクで永続化可能。
"""
from __future__ import annotations

import logging
import time
import uuid
from typing import Any

logger = logging.getLogger("dip.request")


def log_request(
    question: str,
    company: str,
    source: str,
    engine: str,
    elapsed_seconds: float,
    response_length: int,
    files_count: int,
    status: str = "success",
    error_message: str = "",
    user: str = "",
) -> None:
    """
    チャットリクエストの詳細をログに記録する。

    Cloud Logging互換のJSON構造化ログとして出力される。
    """
    extra = {
        "request_id": str(uuid.uuid4())[:8],
        "company": company,
        "engine": engine,
        "elapsed": elapsed_seconds,
        "status_code": status,
    }

    logger.info(
        "chat_request | company=%s | source=%s | engine=%s | user=%s | "
        "elapsed=%.1fs | response=%d chars | files=%d | status=%s%s",
        company,
        source,
        engine,
        user or "unknown",
        elapsed_seconds,
        response_length,
        files_count,
        status,
        f" | error={error_message}" if error_message else "",
        extra=extra,
    )
