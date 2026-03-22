"""
backend/api/quality.py — AI品質管理APIエンドポイント

RequestTraceデータをBigQueryから取得し、管理画面に提供する。
"""
from __future__ import annotations

import json
import logging
from fastapi import APIRouter

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["quality"])

_PROJECT_ID = "decision-support-ai"


@router.get("/quality/metrics")
async def quality_metrics(offset: int = 0, limit: int = 50, company: str = "", engine: str = "", user: str = ""):
    """AI品質メトリクスとリクエスト一覧を返す。"""
    try:
        from google.cloud import bigquery
        bq = bigquery.Client(project=_PROJECT_ID)

        # RequestTraceから取得
        where_clauses = ["jsonPayload.message LIKE '%[RequestTrace]%'"]
        if company:
            where_clauses.append(f"jsonPayload.message LIKE '%{company}%'")
        if engine:
            where_clauses.append(f"jsonPayload.message LIKE '%\"{engine}\"%'")
        if user:
            where_clauses.append(f"jsonPayload.message LIKE '%{user}%'")

        where = " AND ".join(where_clauses)

        query = f"""
        SELECT jsonPayload.message AS trace_json, timestamp
        FROM `{_PROJECT_ID}.dip_ops.run_googleapis_com_stdout_*`
        WHERE {where}
        ORDER BY timestamp DESC
        LIMIT {limit} OFFSET {offset}
        """

        results = list(bq.query(query).result())

        traces = []
        for row in results:
            try:
                # "[RequestTrace] {...}" からJSON部分を抽出
                msg = row.trace_json or ""
                json_start = msg.find("{")
                if json_start >= 0:
                    trace = json.loads(msg[json_start:])
                    trace["_timestamp"] = row.timestamp.isoformat() if row.timestamp else ""
                    traces.append(trace)
            except (json.JSONDecodeError, Exception):
                pass

        # 旧フォーマット（chat_request）からもフォールバック取得
        if not traces:
            fallback_query = f"""
            SELECT
                timestamp,
                REGEXP_EXTRACT(jsonPayload.message, r"elapsed=([\\d.]+)") AS elapsed,
                REGEXP_EXTRACT(jsonPayload.message, r"engine=(\\w+)") AS engine,
                REGEXP_EXTRACT(jsonPayload.message, r"company=([^|]+)") AS company,
                REGEXP_EXTRACT(jsonPayload.message, r"user=([^|]+)") AS user,
                REGEXP_EXTRACT(jsonPayload.message, r"status=(\\w+)") AS status
            FROM `{_PROJECT_ID}.dip_ops.run_googleapis_com_stdout_*`
            WHERE jsonPayload.message LIKE "%chat_request%"
            ORDER BY timestamp DESC
            LIMIT {limit} OFFSET {offset}
            """
            fallback_results = list(bq.query(fallback_query).result())
            for row in fallback_results:
                traces.append({
                    "_timestamp": row.timestamp.isoformat() if row.timestamp else "",
                    "who": {"user": (row.user or "").strip(), "company": (row.company or "").strip(), "source": ""},
                    "what": {"question": "", "response_length": 0, "response_status": (row.status or "").strip(), "charts": [], "sources_referenced": []},
                    "pipeline": {"total_seconds": float(row.elapsed) if row.elapsed else 0, "steps": []},
                    "agent": {"engine": (row.engine or "").strip(), "router_model": "", "selected_agent": "", "agent_model": "", "agent_seconds": 0},
                    "error": None,
                })

        # サマリー集計
        total = len(traces)
        success = sum(1 for t in traces if t.get("what", {}).get("response_status") == "success")
        errors = total - success
        elapsed_values = [t.get("pipeline", {}).get("total_seconds", 0) for t in traces if t.get("pipeline", {}).get("total_seconds", 0) > 0]
        avg_elapsed = round(sum(elapsed_values) / len(elapsed_values), 1) if elapsed_values else 0
        sorted_elapsed = sorted(elapsed_values)
        p95 = round(sorted_elapsed[int(len(sorted_elapsed) * 0.95)], 1) if len(sorted_elapsed) >= 5 else (round(sorted_elapsed[-1], 1) if sorted_elapsed else 0)

        # 👍👎
        fb_query = f"""
        SELECT REGEXP_EXTRACT(jsonPayload.message, r"rating=(\\w+)") AS rating
        FROM `{_PROJECT_ID}.dip_ops.run_googleapis_com_stdout_*`
        WHERE jsonPayload.message LIKE "%[Feedback]%"
        """
        fb_results = list(bq.query(fb_query).result())
        good = sum(1 for r in fb_results if r.rating == "good")
        bad = sum(1 for r in fb_results if r.rating == "bad")
        quality_score = round(good / (good + bad) * 100) if (good + bad) > 0 else 0

        return {
            "summary": {
                "total_requests": total,
                "success": success,
                "errors": errors,
                "error_rate": round(errors / total * 100, 1) if total > 0 else 0,
                "avg_elapsed": avg_elapsed,
                "p95_elapsed": p95,
                "quality_score": quality_score,
                "good_count": good,
                "bad_count": bad,
            },
            "traces": traces,
            "has_more": len(traces) == limit,
        }

    except Exception as e:
        logger.warning("[Quality] Metrics failed: %s", e)
        return {
            "summary": {"total_requests": 0, "success": 0, "errors": 0, "error_rate": 0, "avg_elapsed": 0, "p95_elapsed": 0, "quality_score": 0, "good_count": 0, "bad_count": 0},
            "traces": [],
            "has_more": False,
            "error": str(e),
        }
