"""
tests/test_data_catalog.py — データカタログのテスト
"""
from orchestration.data_catalog import _load_local_catalog, _get_tables_from_local, MAX_SELECTED_TABLES


def test_load_local_catalog():
    """ローカルJSONが読み込めること"""
    catalog = _load_local_catalog()
    assert "tables" in catalog
    assert len(catalog["tables"]) > 0


def test_get_tables_from_local():
    """データセットフィルタが動作すること"""
    tables = _get_tables_from_local("demo_factory02")
    assert len(tables) > 0
    for t in tables:
        assert t["table"].startswith("demo_factory02.")
        assert "description" in t
        assert "tags" in t


def test_get_tables_empty_filter():
    """フィルタなしで全テーブルが返ること"""
    tables = _get_tables_from_local("")
    assert len(tables) > 0


def test_max_selected_tables():
    """選択上限が定義されていること"""
    assert MAX_SELECTED_TABLES == 5
