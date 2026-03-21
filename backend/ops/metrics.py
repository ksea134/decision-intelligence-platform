"""
backend/ops/metrics.py — Cloud Monitoringメトリクス送信

応答時間・エラーカウントをCloud Monitoringのカスタムメトリクスとして送信する。
ローカル環境ではログ出力のみ（Cloud Monitoring APIなし）。
Cloud Run環境ではCloud Monitoring APIに送信。
"""
from __future__ import annotations

import logging
import os
import time

logger = logging.getLogger(__name__)

# Cloud Run環境かどうか（K_SERVICE はCloud Runが自動設定する環境変数）
_IS_CLOUD_RUN = bool(os.environ.get("K_SERVICE"))
_PROJECT_ID = os.environ.get("GCP_PROJECT_ID", "decision-support-ai")

# Cloud Monitoring クライアント（遅延初期化）
_client = None
_project_name = None


def _get_client():
    """Cloud Monitoring クライアントを遅延初期化する。"""
    global _client, _project_name
    if _client is None:
        try:
            from google.cloud import monitoring_v3
            _client = monitoring_v3.MetricServiceClient()
            _project_name = f"projects/{_PROJECT_ID}"
        except Exception as e:
            logger.warning("[Metrics] Cloud Monitoring client init failed: %s", e)
    return _client


def _write_time_series(metric_type: str, value: float, labels: dict[str, str] | None = None):
    """カスタムメトリクスを書き込む。"""
    if not _IS_CLOUD_RUN:
        logger.info("[Metrics] (local) %s = %.2f, labels=%s", metric_type, value, labels)
        return

    try:
        from google.cloud import monitoring_v3
        from google.protobuf import timestamp_pb2

        client = _get_client()
        if not client:
            return

        series = monitoring_v3.TimeSeries()
        series.metric.type = f"custom.googleapis.com/dip/{metric_type}"
        series.resource.type = "generic_task"
        series.resource.labels["project_id"] = _PROJECT_ID
        series.resource.labels["location"] = "asia-northeast1"
        series.resource.labels["namespace"] = "dip"
        series.resource.labels["job"] = "chat"
        series.resource.labels["task_id"] = "0"

        if labels:
            for k, v in labels.items():
                series.metric.labels[k] = v

        now = time.time()
        seconds = int(now)
        nanos = int((now - seconds) * 1e9)

        interval = monitoring_v3.TimeInterval()
        interval.end_time = timestamp_pb2.Timestamp(seconds=seconds, nanos=nanos)

        point = monitoring_v3.Point()
        point.interval = interval
        point.value.double_value = value
        series.points = [point]

        client.create_time_series(name=_project_name, time_series=[series])

    except Exception as e:
        # メトリクス送信失敗はチャット動作に影響させない
        logger.warning("[Metrics] Failed to write %s: %s", metric_type, e)


def record_response_time(elapsed_seconds: float, engine: str, company: str):
    """応答時間をメトリクスとして記録する。"""
    _write_time_series(
        "response_time_seconds",
        elapsed_seconds,
        {"engine": engine, "company": company},
    )


def record_error(engine: str, company: str, error_type: str = "unknown"):
    """エラーをメトリクスとして記録する。"""
    _write_time_series(
        "error_count",
        1.0,
        {"engine": engine, "company": company, "error_type": error_type},
    )
