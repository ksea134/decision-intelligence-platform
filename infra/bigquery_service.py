"""BigQuery Service - Streamlit Cloud 対応版"""
from __future__ import annotations
import logging
import re
from dataclasses import dataclass
from typing import Any

import streamlit as st
from google.cloud import bigquery

from infra.gcp_auth import get_credentials

logger = logging.getLogger(__name__)


SQL_DISALLOWED_KEYWORDS = [
    "INSERT", "UPDATE", "DELETE", "DROP", "CREATE", "ALTER",
    "TRUNCATE", "MERGE", "GRANT", "REVOKE", "EXECUTE", "CALL", "EXEC",
]


class SQLValidationError(Exception):
    pass


@dataclass(frozen=True)
class SQLResult:
    columns: list[str]
    data: list[list[Any]]
    row_count: int

    def to_dataframe(self):
        import pandas as pd
        return pd.DataFrame(self.data, columns=self.columns)


def validate_sql(sql: str) -> None:
    sql_upper = sql.upper().strip()
    if not sql_upper.startswith(("SELECT", "WITH")):
        raise SQLValidationError("SQL must start with SELECT or WITH")
    if ";" in sql:
        raise SQLValidationError("Multiple statements not allowed")
    for kw in SQL_DISALLOWED_KEYWORDS:
        pattern = rf"\b{kw}\b"
        if re.search(pattern, sql_upper):
            raise SQLValidationError(f"Disallowed keyword: {kw}")


class BigQueryService:
    def __init__(self, project_id: str):
        self.project_id = project_id
        self._client: bigquery.Client | None = None

    def _get_client(self) -> bigquery.Client:
        if self._client is None:
            credentials = get_credentials()
            self._client = bigquery.Client(
                project=self.project_id,
                credentials=credentials,
            )
        return self._client

    @st.cache_data(ttl=300, show_spinner=False)
    def fetch_schema(_self, project_id: str, dataset_filter: str | None = None) -> dict:
        """BQスキーマを取得（キャッシュ付き）"""
        try:
            client = _self._get_client()
            datasets = list(client.list_datasets())
            schema = {}
            for ds in datasets:
                ds_id = ds.dataset_id
                if dataset_filter and dataset_filter not in ds_id:
                    continue
                tables = list(client.list_tables(ds.reference))
                schema[ds_id] = {}
                for tbl in tables:
                    full_table = client.get_table(tbl.reference)
                    schema[ds_id][tbl.table_id] = [
                        {"name": f.name, "type": f.field_type, "description": f.description or ""}
                        for f in full_table.schema
                    ]
            return schema
        except Exception as e:
            logger.error(f"Failed to fetch schema: {e}")
            raise

    def execute_sql(self, sql: str, max_rows: int = 100) -> SQLResult:
        """SQLを実行して結果を返す"""
        validate_sql(sql)
        try:
            client = self._get_client()
            query_job = client.query(sql)
            results = query_job.result()
            columns = [f.name for f in results.schema]
            data = [list(row.values()) for row in results][:max_rows]
            return SQLResult(columns=columns, data=data, row_count=len(data))
        except Exception as e:
            logger.error(f"SQL execution failed: {e}")
            raise


# 既存コードとの互換性のための関数インターフェース
_default_service: BigQueryService | None = None


def _get_service(project_id: str) -> BigQueryService:
    global _default_service
    if _default_service is None or _default_service.project_id != project_id:
        _default_service = BigQueryService(project_id)
    return _default_service


def fetch_bq_schema(project_id: str, dataset_filter: str | None = None) -> dict:
    """BQスキーマを取得"""
    service = _get_service(project_id)
    return service.fetch_schema(project_id, dataset_filter)


def execute_bq_sql(project_id: str, sql: str, max_rows: int = 100) -> SQLResult:
    """SQLを実行"""
    service = _get_service(project_id)
    return service.execute_sql(sql, max_rows)
