"""
backend/api/agents.py — エージェント管理APIエンドポイント

config/agents.json から読み込んだエージェント定義の取得・更新を提供する。
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from fastapi import APIRouter
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["agents"])

_AGENTS_JSON_PATH = Path(__file__).parent.parent.parent / "config" / "agents.json"


@router.get("/agents")
async def get_agents():
    """エージェント一覧と現在のモデル設定を返す。"""
    from orchestration.adk.agent_definition import get_agents_info
    return {"agents": get_agents_info()}


@router.get("/agents/detail")
async def get_agents_detail():
    """エージェント一覧（instruction含む）を返す。管理画面用。"""
    try:
        with open(_AGENTS_JSON_PATH, "r", encoding="utf-8") as f:
            config = json.load(f)
        return config
    except Exception as e:
        logger.error("[Agents] Failed to read agents.json: %s", e)
        return {"agents": [], "router": {}}


class UpdateAgentRequest(BaseModel):
    name: str
    instruction: str


@router.post("/agents/update")
async def update_agent(req: UpdateAgentRequest):
    """エージェントのinstructionを更新する。"""
    try:
        with open(_AGENTS_JSON_PATH, "r", encoding="utf-8") as f:
            config = json.load(f)

        # ルーター
        if config.get("router", {}).get("name") == req.name:
            config["router"]["instruction"] = req.instruction
            with open(_AGENTS_JSON_PATH, "w", encoding="utf-8") as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            logger.info("[Agents] Updated router instruction")
            return {"status": "ok", "message": "ルーターのプロンプトを更新しました"}

        # サブエージェント
        for agent in config.get("agents", []):
            if agent["name"] == req.name:
                agent["instruction"] = req.instruction
                with open(_AGENTS_JSON_PATH, "w", encoding="utf-8") as f:
                    json.dump(config, f, ensure_ascii=False, indent=2)
                logger.info("[Agents] Updated %s instruction", req.name)
                return {"status": "ok", "message": f"{agent.get('display_name', req.name)} のプロンプトを更新しました"}

        return {"status": "error", "message": f"エージェント {req.name} が見つかりません"}

    except Exception as e:
        logger.error("[Agents] Update failed: %s", e)
        return {"status": "error", "message": str(e)}
