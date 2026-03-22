"""
tests/test_search_helper.py — 過去事例検索ヘルパーのテスト
"""
from orchestration.search_helper import search_past_qa


class MockSearchClient:
    def __init__(self, results=None, ready=True):
        self._results = results or []
        self._ready = ready

    def is_ready(self):
        return self._ready

    def search(self, query, company, top_k=3):
        return self._results


def test_search_with_results():
    """検索結果がある場合"""
    client = MockSearchClient(results=[
        {"question": "Q1", "answer": "A1"},
        {"question": "Q2", "answer": "A2"},
    ])
    context, detail, count = search_past_qa(client, "テスト", "テスト企業")
    assert count == 2
    assert "Q1" in context
    assert "2件" in detail


def test_search_no_results():
    """検索結果がない場合"""
    client = MockSearchClient(results=[])
    context, detail, count = search_past_qa(client, "テスト", "テスト企業")
    assert count == 0
    assert context == ""
    assert "なし" in detail


def test_search_not_ready():
    """クライアントが未接続の場合"""
    client = MockSearchClient(ready=False)
    context, detail, count = search_past_qa(client, "テスト", "テスト企業")
    assert count == 0
    assert "未接続" in detail


def test_search_none_client():
    """クライアントがNoneの場合"""
    context, detail, count = search_past_qa(None, "テスト", "テスト企業")
    assert count == 0
    assert "未接続" in detail


def test_search_with_trace():
    """trace付きで動作すること"""
    from backend.ops.request_trace import RequestTrace
    trace = RequestTrace()
    client = MockSearchClient(results=[{"question": "Q", "answer": "A"}])
    context, detail, count = search_past_qa(client, "テスト", "テスト企業", trace=trace)
    assert count == 1
    # traceにステップが記録されている
    assert len(trace.steps) == 1
    assert trace.steps[0].step == "past_qa_search"
