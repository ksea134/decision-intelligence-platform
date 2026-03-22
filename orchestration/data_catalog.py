"""
orchestration/data_catalog.py — データカタログインターフェース

Dataplex Data Catalogのローカル版。
段階2でDataplex APIに差し替え予定。このファイルの中身だけ変えれば切り替わる。

責務:
- get_accessible_tables(user, dataset) → 権限フィルタ済みテーブル一覧+メタデータ
- select_relevant_tables(question, table_metadata) → AIエージェントで絞り込み
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_CATALOG_PATH = Path(__file__).parent.parent / "config" / "data_catalog.json"
_catalog: dict | None = None

# テーブル選択の上限
MAX_SELECTED_TABLES = 5


def _load_catalog() -> dict:
    """カタログJSONを読み込む（遅延初期化）。"""
    global _catalog
    if _catalog is None:
        try:
            with open(_CATALOG_PATH, "r", encoding="utf-8") as f:
                _catalog = json.load(f)
        except Exception as e:
            logger.error("[DataCatalog] Failed to load catalog: %s", e)
            _catalog = {"tables": {}, "permissions": {"default": ["*"]}}
    return _catalog


def get_accessible_tables(user: str, dataset_filter: str = "") -> list[dict[str, Any]]:
    """ユーザーがアクセス可能なテーブル一覧とメタデータを返す。

    段階1: 全ユーザーが全テーブルにアクセス可能。
    段階3: Dataplex Governanceから権限を取得して絞り込み。

    Returns:
        [{"table": "dataset.table", "description": "...", "tags": [...], "quality_score": 0.9}, ...]
    """
    catalog = _load_catalog()
    tables = catalog.get("tables", {})

    # 段階1: permissionsは"default": ["*"]で全テーブルアクセス可能
    # 段階3: ここでuser別の権限フィルタを適用

    result = []
    for table_id, meta in tables.items():
        if dataset_filter and not table_id.startswith(dataset_filter + "."):
            continue
        result.append({
            "table": table_id,
            "description": meta.get("description", ""),
            "tags": meta.get("tags", []),
            "quality_score": meta.get("quality_score", 0.0),
        })

    return result


def select_relevant_tables(
    question: str,
    accessible_tables: list[dict[str, Any]],
) -> list[str]:
    """質問に関連するテーブルをAIエージェント（Gemini Flash）で選択する。

    C07例外: テーブル選択は「最適化判断」であり、AIに適した仕事。
    フォールバック: AIが判断できない場合は全テーブルを返す（コード側で保証）。

    Args:
        question: ユーザーの質問文
        accessible_tables: get_accessible_tablesの戻り値

    Returns:
        選択されたテーブル名のリスト（最大MAX_SELECTED_TABLES件）
    """
    if not accessible_tables:
        return []

    # テーブルが少数（5以下）の場合はAI選択不要 — 全テーブル返却
    if len(accessible_tables) <= MAX_SELECTED_TABLES:
        logger.info("[DataCatalog] Tables <= %d, returning all", MAX_SELECTED_TABLES)
        return [t["table"] for t in accessible_tables]

    # AIエージェントにカタログメタデータを渡してテーブル選択
    try:
        from orchestration.llm_client import generate_text
        from config.app_config import MODELS

        # カタログ情報をプロンプトに整形
        catalog_text = "\n".join(
            f"- {t['table']}: {t['description']}（タグ: {', '.join(t['tags'])}）"
            for t in accessible_tables
        )

        prompt = (
            f"以下のテーブル一覧から、ユーザーの質問に回答するために必要なテーブルを最大{MAX_SELECTED_TABLES}個選んでください。\n\n"
            f"【質問】\n{question}\n\n"
            f"【テーブル一覧】\n{catalog_text}\n\n"
            f"【回答形式】\n"
            f"テーブル名だけをカンマ区切りで出力してください。説明は不要です。\n"
            f"例: dataset.table1, dataset.table2, dataset.table3\n"
        )

        result = generate_text(
            model=MODELS.router,  # 高速モデルで選択（Flash）
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
            logger.info("[DataCatalog] AI selected %d/%d tables: %s",
                       len(selected), len(accessible_tables), selected)
            return selected[:MAX_SELECTED_TABLES]

        # AIが有効なテーブル名を返さなかった場合 → フォールバック
        logger.warning("[DataCatalog] AI returned no valid tables, falling back to all")
        return [t["table"] for t in accessible_tables]

    except Exception as e:
        # エラー時はフォールバック（全テーブル）
        logger.warning("[DataCatalog] AI selection failed: %s, falling back to all", e)
        return [t["table"] for t in accessible_tables]
