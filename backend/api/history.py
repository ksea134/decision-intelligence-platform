"""
backend/api/history.py — 質問履歴エンドポイント

Streamlit版のSessionMemory.question_historyと同等の機能を提供する。
企業ごとに直近5件の質問履歴を管理する。
"""
from __future__ import annotations

import time
import logging
from fastapi import APIRouter
from pydantic import BaseModel
from config.app_config import APP

logger = logging.getLogger(__name__)

router = APIRouter(tags=["history"])

# インメモリ履歴ストア（企業名→履歴リスト）
_history_store: dict[str, list[dict]] = {}


class AddHistoryRequest(BaseModel):
    company: str
    text: str


class DeleteHistoryRequest(BaseModel):
    company: str
    entry_id: str


@router.get("/api/history")
def get_history(company: str) -> list[dict]:
    """指定企業の質問履歴を返す。"""
    return _history_store.get(company, [])


@router.post("/api/history/add")
def add_history(req: AddHistoryRequest) -> dict:
    """質問履歴に追加する。"""
    if not req.company or not req.text:
        return {"ok": False}

    entries = _history_store.get(req.company, [])

    # 同じ質問が先頭にあれば追加しない
    if entries and entries[0]["text"] == req.text:
        return {"ok": True}

    entries.insert(0, {
        "id": str(int(time.time() * 1000)),
        "text": req.text,
        "ts": time.strftime("%m/%d %H:%M"),
    })
    _history_store[req.company] = entries[:APP.question_history_max]
    return {"ok": True}


@router.post("/api/history/delete")
def delete_history(req: DeleteHistoryRequest) -> dict:
    """質問履歴から削除する。"""
    entries = _history_store.get(req.company, [])
    _history_store[req.company] = [e for e in entries if e["id"] != req.entry_id]
    return {"ok": True}
