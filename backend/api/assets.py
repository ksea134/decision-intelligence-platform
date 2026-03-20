"""
backend/api/assets.py — 企業アセットエンドポイント

右カラム表示用のデータ（はじめに/前提知識/回答方針/接続状況）を返す。
"""
from __future__ import annotations

import os
import re
import logging

from fastapi import APIRouter, Query
from config.app_config import APP
from config.cloud_config import CloudConfig

logger = logging.getLogger(__name__)

router = APIRouter(tags=["assets"])


@router.get("/api/company-assets")
def get_company_assets(
    folder_name: str = Query(...),
    project_id: str = Query(default=""),
    gcs_bucket: str = Query(default=""),
) -> dict:
    """企業アセット（右カラム表示用）を返す。"""
    from infra.file_loader import load_company_assets
    from orchestration.agents.data_agent import DataAgent

    base_dir = os.path.join("data", folder_name)

    cfg = CloudConfig(
        project_id=project_id,
        gcs_bucket=gcs_bucket,
        folder_name=folder_name,
    )
    agent = DataAgent(cfg)
    data_ctx = agent.fetch_all(base_dir)

    # 優先順位適用後のアセット（BQ接続時はローカル構造化が抑制される等）
    assets = data_ctx.assets

    # BQテーブル一覧
    bq = data_ctx.bq_result
    bq_tables = re.findall(r"Table:\s*(\S+)", bq.content) if bq.is_connected else []

    # GCSファイル一覧
    gcs = data_ctx.gcs_result
    gcs_files = re.findall(r"\[GCS:\s*(.+?)\]", gcs.content) if gcs.is_connected else []

    return {
        "intro_text": assets.intro_text or "",
        "knowledge_text": assets.knowledge_text[:APP.knowledge_preview_len] if assets.knowledge_text else "",
        "knowledge_files": assets.knowledge_files,
        "prompt_text": assets.prompt_text or "",
        "bq": {
            "is_connected": bq.is_connected,
            "is_error": bq.is_error,
            "table_count": len(bq_tables),
            "tables": bq_tables,
            "error_detail": bq.error_detail if bq.is_error else "",
        },
        "gcs": {
            "is_connected": gcs.is_connected,
            "is_error": gcs.is_error,
            "file_count": len(gcs_files),
            "files": gcs_files,
            "error_detail": gcs.error_detail if gcs.is_error else "",
        },
        "local": {
            "structured_files": assets.structured_files,
            "unstructured_files": assets.unstructured_files,
        },
    }
