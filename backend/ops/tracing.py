"""
backend/ops/tracing.py — 分散トレーシング

ローカル: コンソール出力（開発用）
Cloud Run: Cloud Traceに自動連携（OpenTelemetry SDK）

各処理ステップをSpanとして記録し、ボトルネックの特定に使用する。
Cloud Traceへの接続はCloud Run環境で自動的に有効になる。
"""
from __future__ import annotations

import logging
import time
from contextlib import contextmanager
from typing import Any, Generator

logger = logging.getLogger("dip.trace")

# OpenTelemetry SDK（Cloud Run環境で自動接続）
_tracer = None

try:
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor, ConsoleSpanExporter

    # ローカル開発用: コンソール出力
    # Cloud Run環境では google-cloud-opentelemetry パッケージが
    # 自動的にCloud Trace exporterを設定する
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))
    trace.set_tracer_provider(provider)
    _tracer = trace.get_tracer("dip-backend")
    logger.info("OpenTelemetry tracer initialized")
except ImportError:
    logger.info("OpenTelemetry not installed — tracing disabled (install with: pip install opentelemetry-sdk)")


@contextmanager
def trace_span(name: str, attributes: dict[str, Any] | None = None) -> Generator[dict, None, None]:
    """
    処理ステップをSpanとして記録する。

    Usage:
        with trace_span("データ取得", {"tables": 12}) as span_data:
            # 処理
            span_data["rows"] = 542

    OpenTelemetryが未インストールの場合はログ出力のみ。
    """
    start = time.time()
    span_data: dict[str, Any] = {}

    if _tracer:
        with _tracer.start_as_current_span(name, attributes=attributes or {}) as span:
            try:
                yield span_data
                elapsed = round(time.time() - start, 3)
                span.set_attribute("elapsed_seconds", elapsed)
                for k, v in span_data.items():
                    span.set_attribute(k, str(v) if not isinstance(v, (int, float, bool)) else v)
                logger.info("[TRACE] %s: %.3f秒 %s", name, elapsed, span_data or "")
            except Exception as e:
                span.set_attribute("error", True)
                span.set_attribute("error.message", str(e))
                raise
    else:
        # OpenTelemetry未インストール時はログのみ
        try:
            yield span_data
            elapsed = round(time.time() - start, 3)
            logger.info("[TRACE] %s: %.3f秒 %s", name, elapsed, span_data or "")
        except Exception as e:
            elapsed = round(time.time() - start, 3)
            logger.error("[TRACE] %s: %.3f秒 ERROR %s", name, elapsed, e)
            raise
