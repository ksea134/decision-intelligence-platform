"""
tests/test_workflow.py — LangGraph ワークフローのテスト

【テスト内容】
1. 意図分類（Router）のテスト — キーワードベース
2. 各エージェントへのルーティングテスト
3. ワークフロー全体の実行テスト — キーワードベース
4. RouterAgent の単体テスト（モック使用）
5. ワークフロー全体の実行テスト — LLM ベース（モック使用）

【修正履歴】
- 2026-03-16: Step 2 - LLM ベース Router のテストを追加
"""
import sys
import os
import json
from unittest.mock import Mock, MagicMock

# パスを追加（テスト実行用）
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from orchestration.graph.state import create_initial_state, WorkflowState
from orchestration.graph.workflow import (
    classify_intent_keyword,
    create_classify_intent_node,
    route_by_intent,
    run_workflow,
    compile_workflow,
)
from orchestration.agents.router_agent import RouterAgent


def test_classify_intent_analysis():
    """要因分析の意図を正しく分類できるか（キーワードベース）"""
    print("\n" + "=" * 60)
    print("テスト1: 要因分析の意図分類（キーワードベース）")
    print("=" * 60)
    
    state = create_initial_state(
        user_prompt="売上が下がった原因は何ですか？",
        display_label="売上が下がった原因は何ですか？",
        company="テスト株式会社",
        company_folder="test_company",
    )
    
    result = classify_intent_keyword(state)
    
    print(f"質問: {state['user_prompt']}")
    print(f"分類結果: {result['classification']}")
    
    assert result["classification"]["intent"] == "analysis", \
        f"Expected 'analysis', got '{result['classification']['intent']}'"
    assert result["classification"]["confidence"] >= 0.7, \
        f"Expected confidence >= 0.7, got {result['classification']['confidence']}"
    
    print("✅ テスト1 成功: 要因分析として正しく分類されました")


def test_classify_intent_comparison():
    """比較の意図を正しく分類できるか（キーワードベース）"""
    print("\n" + "=" * 60)
    print("テスト2: 比較の意図分類（キーワードベース）")
    print("=" * 60)
    
    state = create_initial_state(
        user_prompt="A製品とB製品の売上を比較してください",
        display_label="A製品とB製品の売上を比較してください",
        company="テスト株式会社",
        company_folder="test_company",
    )
    
    result = classify_intent_keyword(state)
    
    print(f"質問: {state['user_prompt']}")
    print(f"分類結果: {result['classification']}")
    
    assert result["classification"]["intent"] == "comparison", \
        f"Expected 'comparison', got '{result['classification']['intent']}'"
    
    print("✅ テスト2 成功: 比較として正しく分類されました")


def test_classify_intent_forecast():
    """予測の意図を正しく分類できるか（キーワードベース）"""
    print("\n" + "=" * 60)
    print("テスト3: 予測の意図分類（キーワードベース）")
    print("=" * 60)
    
    state = create_initial_state(
        user_prompt="来月の売上予測はどうなりますか？",
        display_label="来月の売上予測はどうなりますか？",
        company="テスト株式会社",
        company_folder="test_company",
    )
    
    result = classify_intent_keyword(state)
    
    print(f"質問: {state['user_prompt']}")
    print(f"分類結果: {result['classification']}")
    
    assert result["classification"]["intent"] == "forecast", \
        f"Expected 'forecast', got '{result['classification']['intent']}'"
    
    print("✅ テスト3 成功: 予測として正しく分類されました")


def test_classify_intent_general():
    """汎用の意図を正しく分類できるか（キーワードベース）"""
    print("\n" + "=" * 60)
    print("テスト4: 汎用の意図分類（キーワードベース）")
    print("=" * 60)
    
    state = create_initial_state(
        user_prompt="会社の概要を教えてください",
        display_label="会社の概要を教えてください",
        company="テスト株式会社",
        company_folder="test_company",
    )
    
    result = classify_intent_keyword(state)
    
    print(f"質問: {state['user_prompt']}")
    print(f"分類結果: {result['classification']}")
    
    assert result["classification"]["intent"] == "general", \
        f"Expected 'general', got '{result['classification']['intent']}'"
    
    print("✅ テスト4 成功: 汎用として正しく分類されました")


def test_route_by_intent():
    """意図に基づくルーティングが正しく動作するか"""
    print("\n" + "=" * 60)
    print("テスト5: ルーティングのテスト")
    print("=" * 60)
    
    test_cases = [
        ("analysis", 0.9, "analysis_agent"),
        ("comparison", 0.85, "comparison_agent"),
        ("forecast", 0.8, "forecast_agent"),
        ("general", 0.5, "general_agent"),
        ("analysis", 0.5, "general_agent"),  # 信頼度が低い場合は汎用
    ]
    
    for intent, confidence, expected_route in test_cases:
        state: WorkflowState = {
            "classification": {
                "intent": intent,
                "confidence": confidence,
                "reasoning": "test",
                "entities": [],
            }
        }
        
        result = route_by_intent(state)
        print(f"  intent={intent}, confidence={confidence} → {result}")
        
        assert result == expected_route, \
            f"Expected '{expected_route}', got '{result}'"
    
    print("✅ テスト5 成功: ルーティングが正しく動作しています")


def test_full_workflow_keyword():
    """ワークフロー全体が正しく動作するか（キーワードベース）"""
    print("\n" + "=" * 60)
    print("テスト6: ワークフロー全体の実行（キーワードベース）")
    print("=" * 60)
    
    result = run_workflow(
        user_prompt="売上が下がった原因を分析してください",
        display_label="売上が下がった原因を分析してください",
        company="テスト株式会社",
        company_folder="test_company",
        use_llm_router=False,  # キーワードベースを使用
    )
    
    print(f"質問: 売上が下がった原因を分析してください")
    print(f"分類結果: {result.get('classification', {}).get('intent')}")
    print(f"実行エージェント: {result.get('current_agent')}")
    print(f"実行時間: {result.get('execution_time_ms', 0):.2f} ms")
    
    # 検証
    assert result.get("classification", {}).get("intent") == "analysis"
    assert result.get("current_agent") == "analysis_agent"
    assert len(result.get("final_response", "")) > 0
    
    print("✅ テスト6 成功: ワークフロー全体が正しく動作しています")


def test_router_agent_with_mock():
    """RouterAgent の単体テスト（モック使用）"""
    print("\n" + "=" * 60)
    print("テスト7: RouterAgent 単体テスト（モック使用）")
    print("=" * 60)
    
    # モックの Gemini Client を作成
    mock_client = Mock()
    mock_response = Mock()
    mock_response.text = json.dumps({
        "intent": "analysis",
        "confidence": 0.92,
        "reasoning": "原因を問う質問パターンを検出しました",
        "entities": ["売上", "下がった", "原因"]
    })
    mock_client.models.generate_content.return_value = mock_response
    
    # RouterAgent を作成
    router = RouterAgent(client=mock_client, fallback_enabled=True)
    
    # 分類を実行
    result = router.classify("売上が下がった原因は何ですか？")
    
    print(f"質問: 売上が下がった原因は何ですか？")
    print(f"分類結果: {dict(result)}")
    
    # 検証
    assert result["intent"] == "analysis"
    assert result["confidence"] == 0.92
    assert "原因を問う" in result["reasoning"]
    
    # API が呼び出されたことを確認
    mock_client.models.generate_content.assert_called_once()
    
    print("✅ テスト7 成功: RouterAgent が正しく動作しています")


def test_router_agent_fallback():
    """RouterAgent のフォールバックテスト"""
    print("\n" + "=" * 60)
    print("テスト8: RouterAgent フォールバックテスト")
    print("=" * 60)
    
    # API エラーをシミュレート
    mock_client = Mock()
    mock_client.models.generate_content.side_effect = Exception("API Error")
    
    # RouterAgent を作成（フォールバック有効）
    router = RouterAgent(client=mock_client, fallback_enabled=True)
    
    # 分類を実行（エラーが発生してもフォールバックで動作する）
    result = router.classify("売上が下がった原因は何ですか？")
    
    print(f"質問: 売上が下がった原因は何ですか？")
    print(f"分類結果（フォールバック）: {dict(result)}")
    
    # フォールバック（キーワードベース）で分類されていることを確認
    assert result["intent"] == "analysis"
    assert "キーワードベース" in result["reasoning"]
    
    print("✅ テスト8 成功: フォールバックが正しく動作しています")


def test_workflow_with_llm_router_mock():
    """ワークフロー全体のテスト（LLM Router + モック）"""
    print("\n" + "=" * 60)
    print("テスト9: ワークフロー全体の実行（LLM Router + モック）")
    print("=" * 60)
    
    # モックの Gemini Client を作成
    mock_client = Mock()
    mock_response = Mock()
    mock_response.text = json.dumps({
        "intent": "comparison",
        "confidence": 0.88,
        "reasoning": "比較を求める質問パターンを検出しました",
        "entities": ["A製品", "B製品", "比較"]
    })
    mock_client.models.generate_content.return_value = mock_response
    
    # ワークフローを実行
    result = run_workflow(
        user_prompt="A製品とB製品を比較してください",
        display_label="A製品とB製品を比較してください",
        company="テスト株式会社",
        company_folder="test_company",
        client=mock_client,
        use_llm_router=True,
    )
    
    print(f"質問: A製品とB製品を比較してください")
    print(f"分類結果: {result.get('classification', {}).get('intent')}")
    print(f"信頼度: {result.get('classification', {}).get('confidence')}")
    print(f"実行エージェント: {result.get('current_agent')}")
    print(f"実行時間: {result.get('execution_time_ms', 0):.2f} ms")
    
    # 検証
    assert result.get("classification", {}).get("intent") == "comparison"
    assert result.get("classification", {}).get("confidence") == 0.88
    assert result.get("current_agent") == "comparison_agent"
    assert len(result.get("final_response", "")) > 0
    
    print("✅ テスト9 成功: LLM Router ワークフローが正しく動作しています")


def run_all_tests():
    """すべてのテストを実行"""
    print("\n" + "=" * 60)
    print("🧪 LangGraph ワークフロー テスト開始")
    print("=" * 60)
    
    try:
        # キーワードベースのテスト
        test_classify_intent_analysis()
        test_classify_intent_comparison()
        test_classify_intent_forecast()
        test_classify_intent_general()
        test_route_by_intent()
        test_full_workflow_keyword()
        
        # LLM ベースのテスト（モック使用）
        test_router_agent_with_mock()
        test_router_agent_fallback()
        test_workflow_with_llm_router_mock()
        
        print("\n" + "=" * 60)
        print("🎉 すべてのテストが成功しました！（9/9）")
        print("=" * 60)
        return True
        
    except AssertionError as e:
        print(f"\n❌ テスト失敗: {e}")
        return False
    except Exception as e:
        print(f"\n❌ エラー発生: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
