"""
backend/ops/request_trace.py — 構造化リクエストトレース（C09準拠）

全リクエストのパイプライン各ステップの時間・ステータス・詳細を記録する。
目的: 問題の特定、責任分解点の明確化、影響範囲の把握、迅速な復旧。
"""
from __future__ import annotations

import json
import logging
import time
import uuid
from dataclasses import dataclass, field, asdict
from typing import Any

logger = logging.getLogger("dip.trace")


@dataclass
class TraceStep:
    step: str
    seconds: float = 0.0
    status: str = "ok"
    detail: str = ""


class RequestTrace:
    """1リクエスト分のトレースを管理する。"""

    def __init__(self, question: str = "", company: str = "", user: str = "", source: str = "", engine: str = ""):
        self.trace_id = f"req-{uuid.uuid4().hex[:8]}"
        self.start_time = time.time()
        self.question = question
        self.company = company
        self.user = user
        self.source = source
        self.engine = engine

        self.steps: list[TraceStep] = []
        self._step_start: float = 0.0

        self.selected_agent = ""
        self.agent_model = ""
        self.router_model = ""
        self.agent_seconds = 0.0

        self.response_length = 0
        self.response_status = "success"
        self.charts: list[str] = []
        self.sources_referenced: list[str] = []

        self.api_calls = 0

        self.error_step = ""
        self.error_type = ""
        self.error_message = ""

    def begin_step(self, step_name: str):
        """ステップの計測を開始する。トレースエラーで本体処理を止めない。"""
        try:
            self._step_start = time.time()
            self._current_step_name = step_name
        except Exception:
            pass

    def end_step(self, detail: str = "", status: str = "ok"):
        """ステップの計測を終了し記録する。トレースエラーで本体処理を止めない。"""
        try:
            elapsed = round(time.time() - self._step_start, 2) if self._step_start else 0
            self.steps.append(TraceStep(
                step=getattr(self, "_current_step_name", "unknown"),
                seconds=elapsed,
                status=status,
                detail=detail,
            ))
            self._step_start = 0
        except Exception:
            pass

    def record_error(self, step: str, error: Exception):
        """エラーを記録する。"""
        self.error_step = step
        self.error_type = type(error).__name__
        self.error_message = str(error)[:500]
        self.response_status = "error"

    def set_agent(self, selected_agent: str, agent_model: str, router_model: str = "", agent_seconds: float = 0):
        """エージェント情報を記録する。"""
        self.selected_agent = selected_agent
        self.agent_model = agent_model
        self.router_model = router_model
        self.agent_seconds = agent_seconds

    def to_dict(self) -> dict[str, Any]:
        """構造化JSONに変換する。"""
        total = round(time.time() - self.start_time, 1)
        return {
            "trace_id": self.trace_id,
            "who": {
                "user": self.user,
                "company": self.company,
                "source": self.source,
            },
            "what": {
                "question": self.question[:200],
                "response_length": self.response_length,
                "response_status": self.response_status,
                "charts": self.charts,
                "sources_referenced": self.sources_referenced,
            },
            "pipeline": {
                "total_seconds": total,
                "steps": [
                    {"step": s.step, "seconds": s.seconds, "status": s.status, "detail": s.detail}
                    for s in self.steps
                ],
            },
            "agent": {
                "engine": self.engine,
                "router_model": self.router_model,
                "selected_agent": self.selected_agent,
                "agent_model": self.agent_model,
                "agent_seconds": self.agent_seconds,
            },
            "api_calls": self.api_calls,
            "error": {
                "step": self.error_step,
                "type": self.error_type,
                "message": self.error_message,
            } if self.error_step else None,
        }

    def emit(self):
        """構造化トレースをログに出力する。"""
        trace_dict = self.to_dict()
        logger.info("[RequestTrace] %s", json.dumps(trace_dict, ensure_ascii=False))
