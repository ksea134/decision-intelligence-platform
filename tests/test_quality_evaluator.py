"""
tests/test_quality_evaluator.py — 品質評価エンジンのテスト
"""
from backend.ops.quality_evaluator import (
    evaluate_response,
    _evaluate_citations,
    _evaluate_length,
    _evaluate_data_references,
)


def test_citations_multiple():
    """出典が複数ある場合"""
    assert _evaluate_citations("回答※1。詳細※2。") == 100


def test_citations_single():
    """出典が1つの場合"""
    assert _evaluate_citations("回答※1。") == 50


def test_citations_none():
    """出典がない場合"""
    assert _evaluate_citations("出典のない回答です。") == 0


def test_length_short():
    """短すぎる回答"""
    assert _evaluate_length("短い") == 10


def test_length_appropriate():
    """適切な長さの回答"""
    answer = "a" * 500
    assert _evaluate_length(answer) == 100


def test_length_long():
    """長すぎる回答"""
    answer = "a" * 6000
    assert _evaluate_length(answer) == 60


def test_data_ref_with_sources():
    """データソースあり"""
    assert _evaluate_data_references("回答", ["BQ:table1", "GCS:file1"]) == 100


def test_data_ref_bq_only():
    """BQのみ"""
    assert _evaluate_data_references("回答", ["BQ:table1"]) == 80


def test_data_ref_no_sources_but_mention():
    """ソースリスト空だが回答にBQ言及"""
    assert _evaluate_data_references("BQ:production_resultsから取得", []) == 70


def test_data_ref_nothing():
    """データ参照なし"""
    assert _evaluate_data_references("一般的な回答です", []) == 0


def test_evaluate_response_overall():
    """全体評価（coherenceはモデルなしで-1）"""
    scores = evaluate_response(
        question="売上教えて",
        answer="売上は100万円です※1。BQ:sales_tableより。" + "a" * 200,
        sources=["BQ:sales_table"],
        model_id="",  # モデルなし→coherence=-1
    )
    assert scores["citation_score"] == 50  # ※1のみ
    assert scores["length_score"] == 100
    assert scores["data_ref_score"] == 80  # BQのみ
    assert scores["coherence_score"] == -1  # モデルなし
    assert scores["overall_score"] > 0


def test_evaluate_response_empty():
    """空の回答"""
    scores = evaluate_response(question="", answer="", sources=[], model_id="")
    assert scores["citation_score"] == 0
    assert scores["length_score"] == 10
    assert scores["overall_score"] >= 0 or scores["overall_score"] == -1
