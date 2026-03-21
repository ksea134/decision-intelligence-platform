"""
backend/api/models.py — モデル設定APIエンドポイント

利用可能モデルの一覧取得と、実行中のモデル切り替えを提供する。
Model Garden段階1: DIP内でモデル管理。段階2以降でGCP API連携予定。
"""
from __future__ import annotations

import logging
from fastapi import APIRouter
from pydantic import BaseModel

from config.app_config import MODELS, ModelConfig

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["models"])


class ModelSwitchRequest(BaseModel):
    role: str   # router / fast / deep / supplement
    model_id: str


@router.get("/models")
async def get_models():
    """利用可能モデル一覧と現在の設定を返す。"""
    return {
        "current": MODELS.to_dict(),
        "available": ModelConfig.AVAILABLE_MODELS,
    }


@router.post("/models/switch")
async def switch_model(req: ModelSwitchRequest):
    """モデルを切り替える（再起動不要）。"""
    valid_roles = ("router", "fast", "deep", "supplement")
    if req.role not in valid_roles:
        return {"error": f"Invalid role: {req.role}. Valid: {valid_roles}"}

    valid_ids = [m["id"] for m in ModelConfig.AVAILABLE_MODELS]
    if req.model_id not in valid_ids:
        return {"error": f"Invalid model_id: {req.model_id}. Valid: {valid_ids}"}

    old_value = getattr(MODELS, req.role)
    setattr(MODELS, req.role, req.model_id)
    logger.info("[Models] Switched %s: %s → %s", req.role, old_value, req.model_id)

    return {
        "message": f"{req.role} を {req.model_id} に切り替えました",
        "current": MODELS.to_dict(),
    }
