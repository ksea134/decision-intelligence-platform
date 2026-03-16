"""
tests/test_reasoning_engine_v2.py — ReasoningEngineV2 のテスト

【テスト内容】
1. run() メソッド（Agent Router 使用）
2. run() メソッド（直接呼び出し）
3. stream_events() メソッド
4. 思考プロセス生成
5. 深掘り質問生成
"""
import sys
import os
from unittest.mock import Mock, MagicMock
from dataclasses import dataclass

# パスを追加
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# -----------------------------------------------------------------------------
# モックデータ
# -----------------------------------------------------------------------------
@dataclass
class MockCloudDataResult:
    content: str = ""
    is_connected: bool = False


@dataclass
class MockAssets:
    knowledge_text: str = "テスト企業は製造業です。"
    prompt_text: str = "丁寧に回答してください。"
    structured_text: str = "売上データ: 100億円"
    unstructured_text: str = "市場分析レポート"


@dataclass
class MockDataContext:
    bq_result: MockCloudDataResult = None
    gcs_result: MockCloudDataResult = None
    assets: MockAssets = None
    bq_connected: bool = False
    
    def __post_init__(self):
        if self.bq_result is None:
            self.bq_result = MockCloudDataResult()
        if self.gcs_result is None:
            self.gcs_result = MockCloudDataResult()
        if self.assets is None:
            self.assets = MockAssets()


@dataclass
class MockCloudConfig:
    folder_name: str = "test_company"
    project_id: str = "test-project"


def create_mock_client():
    """モック Gemini クライアントを作成"""
    mock_client = Mock()
    mock_response = Mock()
    mock_response.text = """
## 分析結果

売上が下がった主な原因は以下の3点です：

1. **季節要因**（寄与度: 45%）
   - 夏季の需要減少

2. **競合参入**（寄与度: 35%）
   - 新規競合の市場参入

3. **価格競争**（寄与度: 20%）
   - 価格競争の激化

[FILES: sales_data.csv, market_analysis.md]
"""
    mock_client.models.generate_content.return_value = mock_response
    return mock_client


# -----------------------------------------------------------------------------
# テスト
# -----------------------------------------------------------------------------
def test_run_with_agent_router():
    """Agent Router を使用した run() のテスト"""
    print("\n" + "=" * 60)
    print("テスト1: run() with Agent Router")
    print("=" * 60)
    
    from orchestration.reasoning_engine_v2 import ReasoningEngineV2
    
    mock_client = create_mock_client()
    mock_data_agent = Mock()
    mock_memory = Mock()
    mock_memory.add_turn = Mock()
    
    engine = ReasoningEngineV2(
        client=mock_client,
        data_agent=mock_data_agent,
        memory=mock_memory,
        use_llm_router=False,  # キーワードベースを使用
        use_llm_agents=False,  # スタブエージェントを使用
    )
    
    result = engine.run(
        user_prompt="売上が下がった原因は何ですか？",
        display_label="売上が下がった原因は何ですか？",
        company="テスト株式会社",
        cfg=MockCloudConfig(),
        data_ctx=MockDataContext(),
        use_agent_router=True,
    )
    
    print(f"結果: {result is not None}")
    print(f"エージェントタイプ: {result.agent_type if result else 'N/A'}")
    print(f"応答長: {len(result.assistant_message['content']) if result else 0} 文字")
    
    assert result is not None
    assert result.agent_type == "analysis"  # キーワード「原因」から analysis に分類
    assert "要因分析" in result.assistant_message["content"]
    
    print("✅ テスト1 成功")


def test_run_direct():
    """直接呼び出し（Agent Router 不使用）のテスト"""
    print("\n" + "=" * 60)
    print("テスト2: run() without Agent Router")
    print("=" * 60)
    
    from orchestration.reasoning_engine_v2 import ReasoningEngineV2
    
    mock_client = create_mock_client()
    mock_data_agent = Mock()
    mock_memory = Mock()
    
    engine = ReasoningEngineV2(
        client=mock_client,
        data_agent=mock_data_agent,
        memory=mock_memory,
    )
    
    result = engine.run(
        user_prompt="会社の概要を教えてください",
        display_label="会社の概要を教えてください",
        company="テスト株式会社",
        cfg=MockCloudConfig(),
        data_ctx=MockDataContext(),
        use_agent_router=False,  # 直接呼び出し
    )
    
    print(f"結果: {result is not None}")
    print(f"エージェントタイプ: {result.agent_type if result else 'N/A'}")
    
    assert result is not None
    assert result.agent_type == "general"
    
    print("✅ テスト2 成功")


def test_stream_events():
    """stream_events() のテスト"""
    print("\n" + "=" * 60)
    print("テスト3: stream_events()")
    print("=" * 60)
    
    from orchestration.reasoning_engine_v2 import ReasoningEngineV2
    
    mock_client = create_mock_client()
    mock_data_agent = Mock()
    mock_memory = Mock()
    
    engine = ReasoningEngineV2(
        client=mock_client,
        data_agent=mock_data_agent,
        memory=mock_memory,
        use_llm_router=False,
        use_llm_agents=False,
    )
    
    events = list(engine.stream_events(
        user_prompt="A製品とB製品を比較してください",
        company="テスト株式会社",
        cfg=MockCloudConfig(),
        data_ctx=MockDataContext(),
        use_agent_router=True,
    ))
    
    print(f"イベント数: {len(events)}")
    
    event_kinds = [e.kind for e in events]
    print(f"イベント種類: {event_kinds}")
    
    # 必須イベントの確認
    assert "status" in event_kinds
    assert "agent_selected" in event_kinds
    assert "text" in event_kinds
    assert "complete" in event_kinds
    
    # エージェント選択イベントの確認
    agent_event = next(e for e in events if e.kind == "agent_selected")
    print(f"選択エージェント: {agent_event.agent_type}")
    assert agent_event.agent_type == "comparison"
    
    print("✅ テスト3 成功")


def test_generate_thought_process():
    """思考プロセス生成のテスト"""
    print("\n" + "=" * 60)
    print("テスト4: generate_thought_process()")
    print("=" * 60)
    
    from orchestration.reasoning_engine_v2 import ReasoningEngineV2
    
    # 思考プロセス用のモック応答を設定
    mock_client = Mock()
    mock_response = Mock()
    mock_response.text = """
**Step 1: データの定量的把握**
- 売上が前年比10%減少
- 競合の市場シェアが5%増加

**Step 2: リスク・文脈の把握**
- 季節要因の影響
- 市場環境の変化

**Step 3: 論点・仮説の統合**
- 複合要因による売上減少
- 対策の優先順位付けが必要

**Step 4: 回答方針**
- 寄与度分析を提示
- 具体的なアクションを提案
"""
    mock_client.models.generate_content.return_value = mock_response
    
    engine = ReasoningEngineV2(
        client=mock_client,
        data_agent=Mock(),
        memory=Mock(),
    )
    
    result = engine.generate_thought_process(
        user_question="売上が下がった原因は？",
        assistant_answer="主な原因は季節要因と競合参入です。",
        agent_type="analysis",
    )
    
    print(f"思考プロセス長: {len(result)} 文字")
    print(f"Step 1 含む: {'Step 1' in result}")
    print(f"Step 4 含む: {'Step 4' in result}")
    
    assert len(result) > 0
    assert "Step 1" in result
    assert "Step 4" in result
    
    print("✅ テスト4 成功")


def test_generate_deep_dive():
    """深掘り質問生成のテスト"""
    print("\n" + "=" * 60)
    print("テスト5: generate_deep_dive()")
    print("=" * 60)
    
    from orchestration.reasoning_engine_v2 import ReasoningEngineV2
    
    # 深掘り質問用のモック応答を設定
    mock_client = Mock()
    mock_response = Mock()
    mock_response.text = '["季節要因の具体的な影響度はどの程度ですか？", "競合他社の参入時期はいつ頃でしたか？", "価格競争への対策は検討していますか？"]'
    mock_client.models.generate_content.return_value = mock_response
    
    engine = ReasoningEngineV2(
        client=mock_client,
        data_agent=Mock(),
        memory=Mock(),
    )
    
    result = engine.generate_deep_dive(
        user_question="売上が下がった原因は？",
        assistant_answer="主な原因は季節要因と競合参入です。",
        agent_type="analysis",
        count=3,
    )
    
    print(f"深掘り質問数: {len(result)}")
    for i, q in enumerate(result, 1):
        print(f"  {i}. {q}")
    
    assert len(result) == 3
    assert all(isinstance(q, str) for q in result)
    
    print("✅ テスト5 成功")


def test_intent_routing():
    """意図分類によるルーティングのテスト"""
    print("\n" + "=" * 60)
    print("テスト6: 意図分類ルーティング")
    print("=" * 60)
    
    from orchestration.reasoning_engine_v2 import ReasoningEngineV2
    
    mock_client = create_mock_client()
    
    engine = ReasoningEngineV2(
        client=mock_client,
        data_agent=Mock(),
        memory=Mock(),
        use_llm_router=False,  # キーワードベース
        use_llm_agents=False,  # スタブ
    )
    
    test_cases = [
        ("売上が下がった原因は？", "analysis"),
        ("A製品とB製品を比較して", "comparison"),
        ("来月の売上予測は？", "forecast"),
        ("会社の概要を教えて", "general"),
    ]
    
    for prompt, expected_agent in test_cases:
        result = engine.run(
            user_prompt=prompt,
            display_label=prompt,
            company="テスト",
            cfg=MockCloudConfig(),
            data_ctx=MockDataContext(),
            use_agent_router=True,
        )
        
        actual_agent = result.agent_type if result else "N/A"
        status = "✓" if actual_agent == expected_agent else "✗"
        print(f"  {status} '{prompt[:20]}...' → {actual_agent} (期待: {expected_agent})")
        
        assert actual_agent == expected_agent, f"Expected {expected_agent}, got {actual_agent}"
    
    print("✅ テスト6 成功")


def run_all_tests():
    """すべてのテストを実行"""
    print("\n" + "=" * 60)
    print("🧪 ReasoningEngineV2 テスト開始")
    print("=" * 60)
    
    try:
        test_run_with_agent_router()
        test_run_direct()
        test_stream_events()
        test_generate_thought_process()
        test_generate_deep_dive()
        test_intent_routing()
        
        print("\n" + "=" * 60)
        print("🎉 すべてのテストが成功しました！（6/6）")
        print("=" * 60)
        return True
        
    except AssertionError as e:
        print(f"\n❌ テスト失敗: {e}")
        import traceback
        traceback.print_exc()
        return False
    except Exception as e:
        print(f"\n❌ エラー発生: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
