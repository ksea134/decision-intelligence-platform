"""
orchestration/data_catalog.py — データカタログインターフェース

段階2: Dataplex Data Catalog API経由でテーブルメタデータを取得。
API接続失敗時はローカルJSON（config/data_catalog.json）にフォールバック。

責務:
- get_accessible_tables(user, dataset) → 権限フィルタ済みテーブル一覧+メタデータ
- select_relevant_tables(question, table_metadata) → AIエージェントで絞り込み
"""
from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_CATALOG_PATH = Path(__file__).parent.parent / "config" / "data_catalog.json"
_PROJECT_ID = "decision-support-ai"

# テーブル選択の上限
MAX_SELECTED_TABLES = 5

# Data Catalog APIキャッシュ（TTL: 5分）
_api_cache: dict[str, tuple[float, list[dict]]] = {}
_CACHE_TTL = 300


# ============================================================
# ローカルJSON版（フォールバック用）
# ============================================================

_local_catalog: dict | None = None


def _load_local_catalog() -> dict:
    """ローカルJSONカタログを読み込む。"""
    global _local_catalog
    if _local_catalog is None:
        try:
            with open(_CATALOG_PATH, "r", encoding="utf-8") as f:
                _local_catalog = json.load(f)
        except Exception as e:
            logger.error("[DataCatalog] Failed to load local catalog: %s", e)
            _local_catalog = {"tables": {}, "permissions": {"default": ["*"]}}
    return _local_catalog


def _get_tables_from_local(dataset_filter: str) -> list[dict[str, Any]]:
    """ローカルJSONからテーブル一覧を取得。"""
    catalog = _load_local_catalog()
    tables = catalog.get("tables", {})
    result = []
    for table_id, meta in tables.items():
        if dataset_filter and not table_id.startswith(dataset_filter + "."):
            continue
        result.append({
            "table": table_id,
            "description": meta.get("description", ""),
            "tags": meta.get("tags", []),
            "columns": [],
            "quality_score": meta.get("quality_score", 0.0),
            "source": "local_json",
        })
    return result


# ============================================================
# Dataplex Data Catalog API版
# ============================================================

def _get_tables_from_api(dataset_filter: str) -> list[dict[str, Any]]:
    """Dataplex Data Catalog APIからテーブル一覧+メタデータを取得。"""
    cache_key = f"api:{dataset_filter}"
    now = time.time()

    # キャッシュ確認
    global last_api_call_count
    if cache_key in _api_cache:
        cached_time, cached_data = _api_cache[cache_key]
        if now - cached_time < _CACHE_TTL:
            last_api_call_count = 0
            logger.info("[DataCatalog] API cache hit: %s (%d tables, 0 API calls)", dataset_filter, len(cached_data))
            return cached_data

    try:
        from google.cloud import datacatalog_v1

        client = datacatalog_v1.DataCatalogClient()
        _api_call_count = 0

        # データセット内の全テーブルを検索
        scope = datacatalog_v1.types.SearchCatalogRequest.Scope()
        scope.include_project_ids.append(_PROJECT_ID)

        query = f"system=bigquery type=TABLE"
        if dataset_filter:
            query += f" parent:{dataset_filter}"

        search_results = client.search_catalog(scope=scope, query=query)
        _api_call_count += 1  # search_catalog

        result = []
        for search_result in search_results:
            fqn = search_result.fully_qualified_name  # bigquery:project.dataset.table
            # "bigquery:project.dataset.table" → "dataset.table"
            parts = fqn.split(":")[-1].split(".")
            if len(parts) >= 3:
                table_id = f"{parts[1]}.{parts[2]}"
            else:
                table_id = fqn

            # search_catalogの結果からdescriptionを取得（lookup_entryは呼ばない = 高速）
            description = search_result.description or ""
            columns = []
            auto_tags = []

            result.append({
                "table": table_id,
                "description": description or f"テーブル: {table_id}（カラム: {', '.join(auto_tags[:5])}）",
                "tags": auto_tags,
                "columns": columns,
                "quality_score": 0.0,
                "source": "dataplex_api",
            })

        # キャッシュに保存
        _api_cache[cache_key] = (now, result)
        last_api_call_count = _api_call_count
        logger.info("[DataCatalog] API fetched: %s → %d tables (%d API calls)", dataset_filter, len(result), _api_call_count)
        return result

    except Exception as e:
        logger.warning("[DataCatalog] API failed: %s, falling back to local JSON", e)
        return []


# ============================================================
# 公開インターフェース
# ============================================================

last_api_call_count = 0

def get_accessible_tables(user: str, dataset_filter: str = "") -> list[dict[str, Any]]:
    """ユーザーがアクセス可能なテーブル一覧とメタデータを返す。

    段階2: Dataplex Data Catalog APIから取得。失敗時はローカルJSONにフォールバック。
    段階3: Dataplex Governanceで権限フィルタを追加予定。
    """
    # まずAPIを試行
    tables = _get_tables_from_api(dataset_filter)

    # API失敗時はローカルJSONにフォールバック
    if not tables:
        tables = _get_tables_from_local(dataset_filter)
        if tables:
            logger.info("[DataCatalog] Fallback to local JSON: %d tables", len(tables))

    return tables


def select_relevant_tables(
    question: str,
    accessible_tables: list[dict[str, Any]],
) -> list[str]:
    """質問に関連するテーブルをAIエージェント（Gemini Flash）で選択する。

    C07例外: テーブル選択は「最適化判断」であり、AIに適した仕事。
    フォールバック: AIが判断できない場合は全テーブルを返す（コード側で保証）。
    """
    if not accessible_tables:
        return []

    # テーブルが少数（5以下）の場合はAI選択不要
    if len(accessible_tables) <= MAX_SELECTED_TABLES:
        logger.info("[DataCatalog] Tables <= %d, returning all", MAX_SELECTED_TABLES)
        return [t["table"] for t in accessible_tables]

    # AIエージェントにカタログメタデータを渡してテーブル選択
    try:
        from orchestration.llm_client import generate_text
        from config.app_config import MODELS

        # カタログ情報をプロンプトに整形（description + カラム名）
        catalog_lines = []
        for t in accessible_tables:
            cols = ", ".join(c["name"] for c in t.get("columns", [])[:8])
            desc = t["description"]
            if cols and t.get("source") == "dataplex_api":
                catalog_lines.append(f"- {t['table']}: {desc}（カラム: {cols}）")
            else:
                tags = ", ".join(t.get("tags", [])[:5])
                catalog_lines.append(f"- {t['table']}: {desc}（タグ: {tags}）")

        catalog_text = "\n".join(catalog_lines)

        prompt = (
            f"以下のテーブル一覧から、ユーザーの質問に回答するために必要なテーブルを最大{MAX_SELECTED_TABLES}個選んでください。\n\n"
            f"【質問】\n{question}\n\n"
            f"【テーブル一覧】\n{catalog_text}\n\n"
            f"【回答形式】\n"
            f"テーブル名だけをカンマ区切りで出力してください。説明は不要です。\n"
            f"例: dataset.table1, dataset.table2, dataset.table3\n"
        )

        result = generate_text(
            model=MODELS.router,
            contents=prompt,
            temperature=0.0,
        )

        # レスポンスからテーブル名を抽出
        all_table_names = {t["table"] for t in accessible_tables}
        selected = []
        for part in result.replace("\n", ",").split(","):
            name = part.strip()
            if name in all_table_names:
                selected.append(name)

        if selected:
            logger.info("[DataCatalog] AI selected %d/%d tables (1 LLM call): %s",
                       len(selected), len(accessible_tables), selected)
            return selected[:MAX_SELECTED_TABLES]

        logger.warning("[DataCatalog] AI returned no valid tables, falling back to all")
        return [t["table"] for t in accessible_tables]

    except Exception as e:
        logger.warning("[DataCatalog] AI selection failed: %s, falling back to all", e)
        return [t["table"] for t in accessible_tables]
