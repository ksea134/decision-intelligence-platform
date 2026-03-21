"""
backend/api/auth.py — ログインユーザー情報API

IAPヘッダーからメールアドレスを取得し、名前に変換して返す。
ローカル環境（IAPなし）ではダミー値を返す。
"""
from __future__ import annotations

from fastapi import APIRouter, Request

router = APIRouter(prefix="/api", tags=["auth"])


def _email_to_name(email: str) -> str:
    """メールアドレスから表示名を推測する。

    例: hideki.koya@company.com → Hideki Koya
        tanaka_taro@company.com → Tanaka Taro
    """
    local = email.split("@")[0]  # @ より前
    parts = local.replace("_", ".").replace("-", ".").split(".")
    return " ".join(p.capitalize() for p in parts if p)


@router.get("/me")
async def get_me(request: Request):
    # IAPが付与するヘッダーからメールを取得
    iap_email = request.headers.get("X-Goog-Authenticated-User-Email", "")

    if iap_email:
        # IAPヘッダーは "accounts.google.com:user@example.com" 形式
        email = iap_email.split(":")[-1] if ":" in iap_email else iap_email
    else:
        # ローカル環境（IAPなし）
        email = "local-dev@example.com"

    return {
        "email": email,
        "name": _email_to_name(email),
        "role": "全企業アクセス",
    }
