from __future__ import annotations
import logging
from domain.models import CloudDataResult, SQLResult
from domain.sql_validator import validate_sql, SQLValidationError
from config.app_config import APP

logger = logging.getLogger(__name__)


def classify_cloud_error(exc: Exception) -> tuple[str, str]:
    s = str(exc).lower()
    if any(k in s for k in ("credentials", "permission", "forbidden", "403", "401")):
        return "auth", str(exc)[:APP.error_msg_limit]
    if any(k in s for k in ("not found", "404", "does not exist")):
        return "not_found", str(exc)[:APP.error_msg_limit]
    if any(k in s for k in ("timeout", "connection", "dns", "network")):
        return "network", str(exc)[:APP.error_msg_limit]
    return "config", str(exc)[:APP.error_msg_limit]


def fetch_bq_schema(project_id: str, dataset_id: str) -> CloudDataResult:
    full = project_id + "." + dataset_id
    try:
        from google.cloud import bigquery
        import pandas as pd
        client = bigquery.Client(project=project_id)
        info_sql = (
            "SELECT table_name, column_name, data_type, description"
            " FROM `" + project_id + "." + dataset_id + ".INFORMATION_SCHEMA.COLUMN_FIELD_PATHS`"
            " ORDER BY table_name, ordinal_position"
        )
        try:
            df = client.query(info_sql).to_dataframe()
        except Exception:
            tables = list(client.list_tables(full))
            if not tables:
                return CloudDataResult(content="BigQuery: " + full + " (no tables)", is_connected=True)
            rows = []
            for t in tables:
                tbl = client.get_table(project_id + "." + dataset_id + "." + t.table_id)
                for fld in tbl.schema:
                    rows.append({
                        "table_name": t.table_id,
                        "column_name": fld.name,
                        "data_type": fld.field_type,
                        "description": fld.description or "",
                    })
            df = pd.DataFrame(rows)

        if df.empty:
            return CloudDataResult(content="BigQuery: " + full + " (no tables)", is_connected=True)

        lines = ["BigQuery Dataset: " + full]
        for tname, grp in df.groupby("table_name", sort=True):
            lines.append("  Table: " + str(tname))
            for _, row in grp.iterrows():
                desc = ": " + str(row["description"]) if row.get("description") else ""
                lines.append("    - " + str(row["column_name"]) + " (" + str(row["data_type"]) + ")" + desc)
        return CloudDataResult(content="\n".join(lines), is_connected=True)

    except Exception as exc:
        etype, edetail = classify_cloud_error(exc)
        logger.error("BQ schema failed [%s]: %s", etype, edetail)
        return CloudDataResult(content="", is_connected=False, error_type=etype, error_detail=edetail)


def execute_bq_sql(project_id: str, sql: str) -> SQLResult | None:
    try:
        validated = validate_sql(sql)
    except SQLValidationError as exc:
        logger.warning("SQL rejected: %s", exc)
        return None
    try:
        from google.cloud import bigquery
        df = bigquery.Client(project=project_id).query(validated).to_dataframe()
        return SQLResult(
            columns=list(df.columns),
            data=df.to_dict(orient="list"),
            row_count=len(df),
        )
    except Exception as exc:
        logger.warning("SQL execution failed: %s", exc)
        return None
