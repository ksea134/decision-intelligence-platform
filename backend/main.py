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
from backend.api.catalog import router as catalog_router
from backend.api.quality import router as quality_router
from backend.api.admin_smart_cards import router as admin_smart_cards_router
from backend.api.admin_table_preview import router as admin_table_preview_router

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
app.include_router(catalog_router)
app.include_router(quality_router)
app.include_router(admin_smart_cards_router)
app.include_router(admin_table_preview_router)

# Data Catalogキャッシュのウォームアップ（初回リクエストの遅延防止）
@app.on_event("startup")
async def _warmup():
    try:
        from orchestration.data_catalog import warmup_cache
        warmup_cache()
    except Exception:
        pass  # ウォームアップ失敗はアプリ起動を止めない

# 静的ファイル配信（Next.js静的エクスポート）
static_dir = Path(__file__).parent.parent / "static"
if static_dir.exists():
    from fastapi.responses import FileResponse

    # /admin → admin.html（Next.jsの静的エクスポートがadmin.htmlを生成するため）
    # HTMLはキャッシュ無効化（JSはNext.jsがハッシュ付きファイル名で管理）
    _no_cache = {"Cache-Control": "no-cache, no-store, must-revalidate"}

    @app.get("/admin")
    async def admin_page():
        admin_html = static_dir / "admin.html"
        if admin_html.exists():
            return FileResponse(str(admin_html), headers=_no_cache)
        return FileResponse(str(static_dir / "index.html"), headers=_no_cache)

    @app.get("/")
    async def index_page():
        return FileResponse(str(static_dir / "index.html"), headers=_no_cache)

    from starlette.staticfiles import StaticFiles as _StaticFiles
    from starlette.responses import Response

    class NoCacheStaticFiles(_StaticFiles):
        """HTMLファイルにはキャッシュ無効ヘッダーを付与する。JSやCSSはNext.jsのハッシュ付きファイル名で管理されるため不要。"""
        async def get_response(self, path: str, scope) -> Response:
            resp = await super().get_response(path, scope)
            if resp.media_type and "html" in resp.media_type:
                resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            return resp

    app.mount("/", NoCacheStaticFiles(directory=str(static_dir), html=True), name="static")
