"""
backend/main.py — FastAPIエントリポイント

Phase 5: Streamlit → FastAPI移行のバックエンド。
既存のOrchestration層・Domain層・Infra層をそのまま活用し、
REST API + SSEストリーミングでフロントエンドに提供する。
"""
from __future__ import annotations

import os
import sys

# プロジェクトルートをパスに追加（既存コードのimportを維持）
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from backend.ops.logging_config import setup_logging

# ログ設定（アプリ全体でINFO以上を出力）
setup_logging()

from backend.api.health import router as health_router
from backend.api.companies import router as companies_router
from backend.api.smart_cards import router as smart_cards_router
from backend.api.chat import router as chat_router
from backend.api.supplement import router as supplement_router
from backend.api.assets import router as assets_router
from backend.api.history import router as history_router
from backend.api.auth import router as auth_router
from backend.api.models import router as models_router
from backend.api.agents import router as agents_router
from backend.api.feedback import router as feedback_router

app = FastAPI(
    title="DIP API",
    description="Decision Intelligence Platform — Backend API",
    version="5.0.0",
)

# CORS設定（開発時はlocalhostを許可、本番はIAPが認証するため不要）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Next.js開発サーバー
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(companies_router)
app.include_router(smart_cards_router)
app.include_router(chat_router)
app.include_router(supplement_router)
app.include_router(assets_router)
app.include_router(history_router)
app.include_router(auth_router)
app.include_router(models_router)
app.include_router(agents_router)
app.include_router(feedback_router)

# 静的ファイル配信（Next.js静的エクスポート）
static_dir = Path(__file__).parent.parent / "static"
if static_dir.exists():
    app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")
