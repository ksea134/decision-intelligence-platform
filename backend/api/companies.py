"""
backend/api/companies.py — 企業一覧エンドポイント

companies.csvから企業の表示名とフォルダ名の一覧を返す。
"""
from __future__ import annotations

from fastapi import APIRouter
from infra.file_loader import load_companies
from config.app_config import APP

router = APIRouter(tags=["companies"])


@router.get("/api/companies")
def get_companies() -> list[dict]:
    """企業一覧を返す。"""
    companies = load_companies(APP.companies_csv_path)
    return [
        {"display_name": display_name, "folder_name": folder_name}
        for display_name, folder_name in companies.items()
    ]
