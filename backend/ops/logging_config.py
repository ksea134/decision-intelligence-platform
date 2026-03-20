"""
backend/ops/logging_config.py — ログ設定

ローカル: 標準出力にJSON構造化ログ
Cloud Run: Cloud Loggingに自動連携（stdout→Cloud Logging）

Cloud Runでは stdout に出力したJSON形式のログが
自動的にCloud Loggingに取り込まれる（追加設定不要）。
"""
from __future__ import annotations

import json
import logging
import sys
import time
from typing import Any


class StructuredFormatter(logging.Formatter):
    """JSON構造化ログフォーマッタ。Cloud Logging互換。"""

    def format(self, record: logging.LogRecord) -> str:
        log_entry: dict[str, Any] = {
            "timestamp": self.formatTime(record),
            "severity": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
        }
        if record.exc_info and record.exc_info[0]:
            log_entry["exception"] = self.formatException(record.exc_info)
        # カスタム属性（リクエストログ用）
        for attr in ("request_id", "company", "engine", "elapsed", "status_code"):
            if hasattr(record, attr):
                log_entry[attr] = getattr(record, attr)
        return json.dumps(log_entry, ensure_ascii=False)


def setup_logging(level: int = logging.INFO) -> None:
    """
    アプリケーション全体のログ設定を行う。
    FastAPI起動時に1回だけ呼ぶ。
    """
    root = logging.getLogger()
    root.setLevel(level)

    # 既存ハンドラをクリア（重複防止）
    root.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)
    handler.setFormatter(StructuredFormatter())
    root.addHandler(handler)

    # uvicornのログもINFOレベルに
    for name in ("uvicorn", "uvicorn.access", "uvicorn.error"):
        logging.getLogger(name).setLevel(level)
