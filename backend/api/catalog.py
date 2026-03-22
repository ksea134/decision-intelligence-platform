"""
backend/api/catalog.py — データカタログAPI

テーブル一覧・説明設定状況の取得、テーブル/カラム説明の更新を提供する。
管理画面（/admin）とサイドバーのカタログヘルスで使用。
"""
from __future__ import annotations

import logging
import time as _time
from fastapi import APIRouter
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["catalog"])

_PROJECT_ID = "decision-support-ai"

# キャッシュ（5分TTL）
_health_cache: dict | None = None
_health_cache_time: float = 0
_CACHE_TTL = 300


def _get_dc_client():
    from google.cloud import datacatalog_v1
    return datacatalog_v1.DataCatalogClient()


@router.get("/catalog/health")
async def catalog_health():
    """全データセットのテーブル説明設定状況を返す（5分キャッシュ付き）。"""
    global _health_cache, _health_cache_time
    now = _time.time()
    if _health_cache and now - _health_cache_time < _CACHE_TTL:
        logger.info("[Catalog] Health cache hit")
        return _health_cache

    try:
        from google.cloud import datacatalog_v1
        client = _get_dc_client()
        scope = datacatalog_v1.types.SearchCatalogRequest.Scope()
        scope.include_project_ids.append(_PROJECT_ID)

        results = client.search_catalog(scope=scope, query="system=bigquery type=TABLE")

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

            if dataset == "dip_ops":
                continue

            # カラム説明状況を確認
            columns_total = 0
            columns_with_desc = 0
            try:
                request = datacatalog_v1.LookupEntryRequest(linked_resource=entry.linked_resource)
                detail = client.lookup_entry(request=request)
                if detail.schema and detail.schema.columns:
                    columns_total = len(detail.schema.columns)
                    columns_with_desc = sum(1 for c in detail.schema.columns if c.description)
            except Exception:
                pass

            tables.append({
                "table": table_id,
                "dataset": dataset,
                "has_description": bool(entry.description),
                "description": entry.description or "",
                "linked_resource": entry.linked_resource,
                "columns_total": columns_total,
                "columns_with_desc": columns_with_desc,
            })

        # 重複除去
        seen = set()
        unique_tables = []
        for t in tables:
            if t["table"] not in seen:
                seen.add(t["table"])
                unique_tables.append(t)

        total = len(unique_tables)
        with_desc = sum(1 for t in unique_tables if t["has_description"])

        result = {
            "total": total,
            "with_description": with_desc,
            "without_description": total - with_desc,
            "tables": unique_tables,
        }
        _health_cache = result
        _health_cache_time = now
        logger.info("[Catalog] Health fetched and cached: %d tables", total)
        return result

    except Exception as e:
        logger.warning("[Catalog] Health check failed: %s", e)
        return {"total": 0, "with_description": 0, "without_description": 0, "tables": [], "error": str(e)}


@router.get("/catalog/table-detail")
async def table_detail(dataset: str, table: str):
    """テーブルの詳細（説明+カラム一覧）を返す。"""
    try:
        from google.cloud import datacatalog_v1
        client = _get_dc_client()

        linked = f"//bigquery.googleapis.com/projects/{_PROJECT_ID}/datasets/{dataset}/tables/{table}"
        request = datacatalog_v1.LookupEntryRequest(linked_resource=linked)
        entry = client.lookup_entry(request=request)

        columns = []
        if entry.schema and entry.schema.columns:
            for col in entry.schema.columns:
                columns.append({
                    "name": col.column,
                    "type": col.type_,
                    "description": col.description or "",
                })

        return {
            "table": f"{dataset}.{table}",
            "description": entry.description or "",
            "columns": columns,
            "entry_name": entry.name,
        }

    except Exception as e:
        logger.warning("[Catalog] Table detail failed: %s", e)
        return {"table": f"{dataset}.{table}", "description": "", "columns": [], "error": str(e)}


class UpdateTableDescRequest(BaseModel):
    dataset: str
    table: str
    description: str


@router.post("/catalog/update")
async def update_table_description(req: UpdateTableDescRequest):
    """テーブルの説明をBigQuery経由で更新する。"""
    try:
        from google.cloud import bigquery
        bq_client = bigquery.Client(project=_PROJECT_ID)

        table_ref = bq_client.get_table(f"{_PROJECT_ID}.{req.dataset}.{req.table}")
        table_ref.description = req.description
        bq_client.update_table(table_ref, ["description"])

        # キャッシュクリア（次回アクセス時に最新を取得）
        global _health_cache
        _health_cache = None

        logger.info("[Catalog] Updated table description: %s.%s", req.dataset, req.table)
        return {"status": "ok", "message": f"{req.dataset}.{req.table} の説明を更新しました"}

    except Exception as e:
        logger.error("[Catalog] Update table description failed: %s", e)
        return {"status": "error", "message": str(e)}


class UpdateColumnDescRequest(BaseModel):
    dataset: str
    table: str
    column: str
    description: str


@router.post("/catalog/update-column")
async def update_column_description(req: UpdateColumnDescRequest):
    """カラムの説明をBigQuery経由で更新する。"""
    try:
        from google.cloud import bigquery
        bq_client = bigquery.Client(project=_PROJECT_ID)

        table_ref = bq_client.get_table(f"{_PROJECT_ID}.{req.dataset}.{req.table}")

        new_schema = []
        found = False
        for field in table_ref.schema:
            if field.name == req.column:
                new_schema.append(field._properties | {"description": req.description})
                found = True
            else:
                new_schema.append(field._properties)

        if not found:
            return {"status": "error", "message": f"カラム {req.column} が見つかりません"}

        table_ref.schema = [bigquery.SchemaField.from_api_repr(s) for s in new_schema]
        bq_client.update_table(table_ref, ["schema"])

        # キャッシュクリア
        _health_cache = None

        logger.info("[Catalog] Updated column description: %s.%s.%s", req.dataset, req.table, req.column)
        return {"status": "ok", "message": f"{req.column} の説明を更新しました"}

    except Exception as e:
        logger.error("[Catalog] Update column description failed: %s", e)
        return {"status": "error", "message": str(e)}
