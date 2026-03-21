"""
backend/api/agents.py — エージェント一覧APIエンドポイント

config/agents.json から読み込んだエージェント定義を返す。
"""
from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/api", tags=["agents"])


@router.get("/agents")
async def get_agents():
    """エージェント一覧と現在のモデル設定を返す。"""
    from orchestration.adk.agent_definition import get_agents_info
    return {"agents": get_agents_info()}
