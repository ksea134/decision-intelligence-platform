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
        "gcp_services": _get_gcp_services(),
    }


def _get_gcp_services() -> list[dict]:
    """利用中・将来利用予定のGCPサービス一覧を返す。"""
    return [
        # 稼働中
        {"name": "Cloud Run", "status": "active", "purpose": "アプリホスティング"},
        {"name": "IAP", "status": "active", "purpose": "ログイン認証"},
        {"name": "BigQuery", "status": "active", "purpose": "構造化データ"},
        {"name": "Cloud Storage", "status": "active", "purpose": "非構造化データ"},
        {"name": "Gemini API", "status": "active", "purpose": "AI回答生成"},
        {"name": "Vertex AI Search", "status": "active", "purpose": "セマンティック検索"},
        {"name": "Cloud Logging", "status": "active", "purpose": "ログ収集"},
        {"name": "Cloud Trace", "status": "active", "purpose": "処理トレース"},
        {"name": "Cloud Monitoring", "status": "active", "purpose": "メトリクス・アラート"},
        {"name": "Looker Studio", "status": "active", "purpose": "フィードバック分析"},
        {"name": "Google ADK", "status": "active", "purpose": "エージェント基盤"},
        # 将来利用予定
        {"name": "Model Garden", "status": "planned", "purpose": "マルチモデル切替"},
        {"name": "Vertex AI Agent Builder", "status": "planned", "purpose": "エージェント管理"},
        {"name": "Vertex AI Evaluation", "status": "planned", "purpose": "回答品質自動評価"},
        {"name": "Cloud DLP", "status": "planned", "purpose": "機密データマスキング"},
        {"name": "Dataplex", "status": "planned", "purpose": "データガバナンス"},
        {"name": "Looker", "status": "planned", "purpose": "BIダッシュボード"},
        {"name": "A2A Protocol", "status": "planned", "purpose": "外部エージェント連携"},
        {"name": "MCP", "status": "planned", "purpose": "ツール接続標準化"},
    ]
