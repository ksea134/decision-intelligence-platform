"""
backend/api/supplement.py — 補足フェーズエンドポイント

メイン回答完了後に、思考ロジック・インフォグラフィック・深掘り質問を生成する。
"""
from __future__ import annotations

import json
import logging
import time

from fastapi import APIRouter
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(tags=["supplement"])


class SupplementRequest(BaseModel):
    """補足フェーズリクエスト。"""
    user_prompt: str
    display_text: str
    company_display_name: str
    company_folder_name: str
    project_id: str = ""
    gcs_bucket: str = ""


@router.post("/api/supplement")
def generate_supplement(request: SupplementRequest) -> dict:
    """思考ロジック + インフォグラフィックを生成する。"""
    start_ts = time.time()

    try:
        from google import genai
        from config.cloud_config import CloudConfig
        from orchestration.reasoning_engine import ReasoningEngine
        from orchestration.agents.data_agent import DataAgent
        from orchestration.memory.session_memory import SessionMemory
        from infra.file_loader import load_company_assets

        import os
        base_dir = os.path.join("data", request.company_folder_name)
        cfg = CloudConfig(
            project_id=request.project_id,
            gcs_bucket=request.gcs_bucket,
            folder_name=request.company_folder_name,
        )

        assets = load_company_assets(base_dir)
        from orchestration.llm_client import _get_gemini_client
        client = _get_gemini_client()
        agent = DataAgent(cfg)
        memory = SessionMemory()
        engine = ReasoningEngine(client=client, data_agent=agent, memory=memory, search_client=None)

        timestamp = time.strftime("%Y%m%d-%H%M")

        from backend.ops.request_trace import RequestTrace
        trace = RequestTrace(
            question=request.user_prompt[:100],
            company=request.company_display_name,
            source="supplement",
            engine="supplement",
        )

        # 思考ロジック
        trace.begin_step("thought_process")
        thought = engine.generate_thought_process(
            request.user_prompt,
            request.display_text,
            assets.structured_text,
            assets.unstructured_text,
        )
        trace.end_step(f"{len(thought)}文字" if thought else "生成失敗")

        # インフォグラフィック
        trace.begin_step("infographic")
        info_html, info_data = engine.generate_infographic(
            request.display_text,
            timestamp,
            request.company_display_name,
        )
        trace.end_step("生成完了" if info_html else "生成失敗")

        elapsed = round(time.time() - start_ts, 1)
        trace.response_status = "success"
        trace.response_length = len(thought or "") + len(info_html or "")
        trace.emit()
        logger.warning("[PERF] /api/supplement: %.1f秒", elapsed)

        return {
            "thought_process": thought,
            "infographic_html": info_html,
            "infographic_data": info_data,
            "elapsed_seconds": elapsed,
        }

    except Exception as e:
        logger.error("[ERROR] /api/supplement: %s", e, exc_info=True)
        return {"error": str(e)}


class DeepDiveRequest(BaseModel):
    """深掘り質問生成リクエスト。"""
    user_prompt: str
    display_text: str
    company_folder_name: str
    project_id: str = ""
    gcs_bucket: str = ""


@router.post("/api/deep-dive")
def generate_deep_dive(request: DeepDiveRequest) -> dict:
    """深掘り質問（3件）を生成する。"""
    try:
        from google import genai
        from config.cloud_config import CloudConfig
        from orchestration.reasoning_engine import ReasoningEngine
        from orchestration.agents.data_agent import DataAgent
        from orchestration.memory.session_memory import SessionMemory

        cfg = CloudConfig(
            project_id=request.project_id,
            gcs_bucket=request.gcs_bucket,
            folder_name=request.company_folder_name,
        )
        from orchestration.llm_client import _get_gemini_client
        client = _get_gemini_client()
        agent = DataAgent(cfg)
        memory = SessionMemory()
        engine = ReasoningEngine(client=client, data_agent=agent, memory=memory, search_client=None)

        questions = engine.generate_deep_dive(request.user_prompt, request.display_text)

        return {"questions": questions}

    except Exception as e:
        logger.error("[ERROR] /api/deep-dive: %s", e, exc_info=True)
        return {"error": str(e)}
