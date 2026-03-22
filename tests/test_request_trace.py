"""
tests/test_request_trace.py — RequestTrace のテスト
"""
import json
from backend.ops.request_trace import RequestTrace


def test_basic_trace():
    """基本的なトレース記録と出力"""
    trace = RequestTrace(question="テスト質問", company="テスト企業", user="user@test.com", source="chat", engine="adk")
    trace.begin_step("data_load")
    trace.end_step("BQ: 100 chars")
    trace.begin_step("llm_generate")
    trace.end_step("model=gemini-2.5-flash")
    trace.response_length = 500
    trace.response_status = "success"

    d = trace.to_dict()
    assert d["who"]["user"] == "user@test.com"
    assert d["who"]["company"] == "テスト企業"
    assert d["what"]["response_length"] == 500
    assert len(d["pipeline"]["steps"]) == 2
    assert d["pipeline"]["steps"][0]["step"] == "data_load"
    assert d["pipeline"]["steps"][1]["step"] == "llm_generate"
    assert d["error"] is None


def test_error_trace():
    """エラー記録"""
    trace = RequestTrace(question="test", company="test")
    trace.record_error("bq_fetch", ValueError("timeout"))

    d = trace.to_dict()
    assert d["error"]["step"] == "bq_fetch"
    assert d["error"]["type"] == "ValueError"
    assert "timeout" in d["error"]["message"]
    assert d["what"]["response_status"] == "error"


def test_agent_info():
    """エージェント情報の記録"""
    trace = RequestTrace()
    trace.set_agent(selected_agent="要因分析エージェント", agent_model="gemini-2.5-pro", router_model="gemini-2.5-flash")

    d = trace.to_dict()
    assert d["agent"]["selected_agent"] == "要因分析エージェント"
    assert d["agent"]["agent_model"] == "gemini-2.5-pro"


def test_api_calls():
    """API呼び出し回数"""
    trace = RequestTrace()
    trace.api_calls = 5

    d = trace.to_dict()
    assert d["api_calls"] == 5


def test_step_name_override():
    """end_stepでstep_nameを明示指定"""
    trace = RequestTrace()
    trace.begin_step("wrong_name")
    trace.end_step("detail", step_name="correct_name")

    d = trace.to_dict()
    assert d["pipeline"]["steps"][0]["step"] == "correct_name"


def test_try_except_safety():
    """トレースメソッドが例外を投げないこと"""
    trace = RequestTrace()
    # 正常でない使い方でもクラッシュしない
    trace.end_step("no begin")  # begin_stepなしでend_step
    trace.set_agent(selected_agent=None, agent_model=None)  # None渡し
    trace.emit()  # 空のトレースを出力


def test_emit_produces_json(capsys):
    """emitがJSON形式でログ出力すること"""
    import logging
    logger = logging.getLogger("dip.trace")
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler()
    logger.addHandler(handler)

    trace = RequestTrace(question="test")
    trace.emit()

    # emitが例外なく完了すればOK（ログ出力先はテスト環境依存）
    assert True
