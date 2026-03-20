"""
backend/api/health.py — ヘルスチェックエンドポイント

Cloud RunのUptime Check、ロードバランサーのヘルスチェックに使用。
"""
from __future__ import annotations

from fastapi import APIRouter
from config.app_config import APP

router = APIRouter(tags=["health"])


@router.get("/api/health")
def health_check() -> dict:
    return {
        "status": "ok",
        "version": APP.version,
    }
