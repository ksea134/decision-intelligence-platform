"""
backend/api/catalog.py — データカタログヘルスチェックAPI

全テーブルの説明設定状況を返す。未設定テーブルを警告表示するために使用。
"""
from __future__ import annotations

import logging
from fastapi import APIRouter

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["catalog"])


@router.get("/catalog/health")
async def catalog_health():
    """全データセットのテーブル説明設定状況を返す。"""
    try:
        from google.cloud import datacatalog_v1

        client = datacatalog_v1.DataCatalogClient()
        scope = datacatalog_v1.types.SearchCatalogRequest.Scope()
        scope.include_project_ids.append("decision-support-ai")

        results = client.search_catalog(
            scope=scope,
            query="system=bigquery type=TABLE",
        )

        tables = []
        for entry in results:
            fqn = entry.fully_qualified_name
            parts = fqn.split(":")[-1].split(".")
            if len(parts) >= 3:
                dataset = parts[1]
                table = parts[2]
                table_id = f"{dataset}.{table}"
            else:
                dataset = ""
                table_id = fqn

            # dip_ops（運用ログ）は除外
            if dataset == "dip_ops":
                continue

            tables.append({
                "table": table_id,
                "dataset": dataset,
                "has_description": bool(entry.description),
                "description": entry.description or "",
            })

        # 重複除去（search_catalogが重複を返すことがある）
        seen = set()
        unique_tables = []
        for t in tables:
            if t["table"] not in seen:
                seen.add(t["table"])
                unique_tables.append(t)

        total = len(unique_tables)
        with_desc = sum(1 for t in unique_tables if t["has_description"])
        without_desc = total - with_desc

        return {
            "total": total,
            "with_description": with_desc,
            "without_description": without_desc,
            "tables": unique_tables,
        }

    except Exception as e:
        logger.warning("[Catalog] Health check failed: %s", e)
        return {
            "total": 0,
            "with_description": 0,
            "without_description": 0,
            "tables": [],
            "error": str(e),
        }
