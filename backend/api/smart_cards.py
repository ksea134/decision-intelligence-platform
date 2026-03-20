"""
backend/api/smart_cards.py — スマートカードエンドポイント

指定された企業のスマートカード一覧を返す。
"""
from __future__ import annotations

import os
from fastapi import APIRouter, Query
from infra.file_loader import load_smart_cards
from config.app_config import PATHS

router = APIRouter(tags=["smart_cards"])


@router.get("/api/smart-cards")
def get_smart_cards(folder_name: str = Query(..., description="企業フォルダ名")) -> list[dict]:
    """指定企業のスマートカード一覧を返す。"""
    smart_cards_dir = os.path.join("data", folder_name, PATHS.smart_cards)
    cards = load_smart_cards(smart_cards_dir)
    # prompt_templateはフロントに送らない（サイズが大きい+セキュリティ）
    return [
        {
            "id": card["id"],
            "icon": card["icon"],
            "title": card["title"],
            "data_source": card["data_source"],
        }
        for card in cards
    ]
