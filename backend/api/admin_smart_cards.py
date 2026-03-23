"""
backend/api/admin_smart_cards.py — スマートカード管理API

管理画面から全企業のスマートカードを一括管理するためのエンドポイント。
"""
from __future__ import annotations

import csv
import os
from pathlib import Path
from typing import Any

from fastapi import APIRouter, UploadFile, File, Form
from fastapi.responses import FileResponse
from pydantic import BaseModel

from config.app_config import PATHS
from infra.file_loader import load_smart_cards, load_companies

router = APIRouter(tags=["admin_smart_cards"])

COMPANIES_CSV = "data/companies.csv"
CSV_HEADER = ["企業コード", "コード", "アイコン", "アイコンタイプ", "タイトル", "データソース", "表示", "エンジン"]


class CardData(BaseModel):
    company_code: str
    id: str
    old_id: str = ""
    icon: str
    icon_type: str = "emoji"
    title: str
    data_source: str = "all"
    visible: bool = True
    engine: str = "v1"
    prompt_template: str = ""


class SaveRequest(BaseModel):
    cards: list[CardData]
    deleted: list[dict[str, str]] = []  # [{"company_code": "xx", "id": "yy"}, ...]


@router.get("/api/admin/smart-cards")
def get_all_smart_cards() -> dict[str, Any]:
    """全企業のスマートカード一覧を返す（prompt含む）。"""
    companies = load_companies(COMPANIES_CSV)  # {display_name: folder_name}
    all_cards: list[dict[str, Any]] = []

    for display_name, folder_name in sorted(companies.items()):
        smart_cards_dir = os.path.join("data", folder_name, PATHS.smart_cards)
        cards = load_smart_cards(smart_cards_dir, include_prompt=True, include_hidden=True)
        for card in cards:
            card["company_code"] = folder_name
            card["company_name"] = display_name
        all_cards.extend(cards)

    return {
        "cards": all_cards,
        "companies": [
            {"folder_name": v, "display_name": k}
            for k, v in sorted(companies.items())
        ],
    }


@router.post("/api/admin/smart-cards/save")
def save_smart_cards(req: SaveRequest) -> dict[str, str]:
    """全企業のスマートカードを一括保存（CSV + .md同時書き込み）。"""
    # 企業ごとにグループ化
    by_company: dict[str, list[CardData]] = {}
    for card in req.cards:
        by_company.setdefault(card.company_code, []).append(card)

    # コード変更時に古いmdファイルを削除
    for card in req.cards:
        if card.old_id and card.old_id != card.id:
            base = Path("data") / card.company_code / PATHS.smart_cards
            for ext in (".md", ".txt"):
                p = base / f"{card.old_id}{ext}"
                if p.exists():
                    p.unlink()

    # 削除対象のmdファイルを削除
    for item in req.deleted:
        company = item.get("company_code", "")
        code = item.get("id", "")
        if company and code:
            base = Path("data") / company / PATHS.smart_cards
            for ext in (".md", ".txt"):
                p = base / f"{code}{ext}"
                if p.exists():
                    p.unlink()

    # リクエストに含まれる企業だけCSV + mdを書き出し
    for folder_name in by_company:
        base = Path("data") / folder_name / PATHS.smart_cards
        base.mkdir(parents=True, exist_ok=True)
        csv_path = base / "smart_cards.csv"

        cards = by_company.get(folder_name, [])

        # CSVを書き出し
        with csv_path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(CSV_HEADER)
            for card in cards:
                writer.writerow([
                    card.company_code,
                    card.id,
                    card.icon,
                    card.icon_type,
                    card.title,
                    card.data_source,
                    "1" if card.visible else "0",
                    card.engine,
                ])

        # mdファイルを書き出し
        for card in cards:
            if card.prompt_template.strip():
                md_path = base / f"{card.id}.md"
                md_path.write_text(card.prompt_template, encoding="utf-8")

    return {"message": f"{len(req.cards)}枚のカードを保存しました"}


@router.post("/api/admin/smart-cards/upload-icon")
async def upload_icon(
    company: str = Form(...),
    file: UploadFile = File(...),
) -> dict[str, str]:
    """アイコン画像をアップロードする。"""
    icon_dir = Path("data") / company / PATHS.smart_cards / "icons"
    icon_dir.mkdir(parents=True, exist_ok=True)

    filename = file.filename or "icon.png"
    dest = icon_dir / filename
    with dest.open("wb") as f:
        content = await file.read()
        f.write(content)

    return {"filename": filename, "path": f"/api/admin/smart-cards/icon/{company}/{filename}"}


@router.get("/api/admin/smart-cards/icon/{company}/{filename}")
def get_icon(company: str, filename: str):
    """アイコン画像を配信する。"""
    icon_path = Path("data") / company / PATHS.smart_cards / "icons" / filename
    if not icon_path.exists():
        return {"error": "not found"}
    return FileResponse(str(icon_path))
