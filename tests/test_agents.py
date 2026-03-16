"""
tests/test_agents.py — 各エージェントの単体テスト

【テスト内容】
1. BaseAgent の基本機能
2. AnalysisAgent のシステムプロンプト
3. ComparisonAgent のシステムプロンプト
4. ForecastAgent のシステムプロンプト
5. GeneralAgent のシステムプロンプト
6. エージェント実行（モック使用）
"""
import sys
import os
import json
from unittest.mock import Mock

# パスを追加（テスト実行用）
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from orchestration.graph.state import create_initial_state


def test_analysis_agent_prompt():
    """AnalysisAgent のシステムプロンプトが正しく構築されるか"""
    print("\n" + "=" * 60)
    print("テスト1: AnalysisAgent のシステムプロンプト")
    print("=" * 60)
    
    from orchestration.agents.analysis_agent import AnalysisAgent
    
    # モッククライアント
    mock_client = Mock()
    agent = AnalysisAgent(client=mock_client)
    
    # 状態を作成
    state = create_initial_state(
        user_prompt="売上が下がった原因は何ですか？",
        display_label="売上が下がった原因は何ですか？",
        company="テスト株式会社",
        company_folder="test_company",
        knowledge="テスト株式会社は製造業です。",
    )
    
    # システムプロンプトを構築
    prompt = agent.build_system_prompt(state)
    
    print(f"プロンプト長: {len(prompt)} 文字")
    print(f"企業名が含まれる: {'テスト株式会社' in prompt}")
    print(f"5 Whys が含まれる: {'5 Whys' in prompt}")
    print(f"寄与度が含まれる: {'寄与度' in prompt}")
    
    # 検証
    assert "テスト株式会社" in prompt
    assert "5 Whys" in prompt or "5つのなぜ" in prompt
    assert "寄与度" in prompt
    assert "製造業" in prompt  # knowledge が含まれる
    
    print("✅ テスト1 成功: AnalysisAgent のプロンプトが正しく構築されました")


def test_comparison_agent_prompt():
    """ComparisonAgent のシステムプロンプトが正しく構築されるか"""
    print("\n" + "=" * 60)
    print("テスト2: ComparisonAgent のシステムプロンプト")
    print("=" * 60)
    
    from orchestration.agents.comparison_agent import ComparisonAgent
    
    mock_client = Mock()
    agent = ComparisonAgent(client=mock_client)
    
    state = create_initial_state(
        user_prompt="A製品とB製品を比較してください",
        display_label="A製品とB製品を比較してください",
        company="サンプル企業",
        company_folder="sample",
    )
    
    prompt = agent.build_system_prompt(state)
    
    print(f"プロンプト長: {len(prompt)} 文字")
    print(f"比較表が含まれる: {'比較表' in prompt}")
    print(f"差分が含まれる: {'差分' in prompt}")
    
    assert "サンプル企業" in prompt
    assert "比較" in prompt
    assert "差分" in prompt
    
    print("✅ テスト2 成功: ComparisonAgent のプロンプトが正しく構築されました")


def test_forecast_agent_prompt():
    """ForecastAgent のシステムプロンプトが正しく構築されるか"""
    print("\n" + "=" * 60)
    print("テスト3: ForecastAgent のシステムプロンプト")
    print("=" * 60)
    
    from orchestration.agents.forecast_agent import ForecastAgent
    
    mock_client = Mock()
    agent = ForecastAgent(client=mock_client)
    
    state = create_initial_state(
        user_prompt="来月の売上予測は？",
        display_label="来月の売上予測は？",
        company="予測テスト社",
        company_folder="forecast_test",
    )
    
    prompt = agent.build_system_prompt(state)
    
    print(f"プロンプト長: {len(prompt)} 文字")
    print(f"シナリオが含まれる: {'シナリオ' in prompt}")
    print(f"楽観が含まれる: {'楽観' in prompt}")
    print(f"悲観が含まれる: {'悲観' in prompt}")
    
    assert "予測テスト社" in prompt
    assert "シナリオ" in prompt
    assert "楽観" in prompt
    assert "悲観" in prompt
    
    print("✅ テスト3 成功: ForecastAgent のプロンプトが正しく構築されました")


def test_general_agent_prompt():
    """GeneralAgent のシステムプロンプトが正しく構築されるか"""
    print("\n" + "=" * 60)
    print("テスト4: GeneralAgent のシステムプロンプト")
    print("=" * 60)
    
    from orchestration.agents.general_agent import GeneralAgent
    
    mock_client = Mock()
    agent = GeneralAgent(client=mock_client)
    
    state = create_initial_state(
        user_prompt="会社の概要を教えてください",
        display_label="会社の概要を教えてください",
        company="汎用テスト社",
        company_folder="general_test",
    )
    
    prompt = agent.build_system_prompt(state)
    
    print(f"プロンプト長: {len(prompt)} 文字")
    print(f"結論が含まれる: {'結論' in prompt}")
    
    assert "汎用テスト社" in prompt
    assert "結論" in prompt or "回答" in prompt
    
    print("✅ テスト4 成功: GeneralAgent のプロンプトが正しく構築されました")


def test_analysis_agent_run_with_mock():
    """AnalysisAgent の実行（モック使用）"""
    print("\n" + "=" * 60)
    print("テスト5: AnalysisAgent の実行（モック）")
    print("=" * 60)
    
    from orchestration.agents.analysis_agent import AnalysisAgent
    
    # モック応答を設定
    mock_client = Mock()
    mock_response = Mock()
    mock_response.text = """
## 要因分析結果

### 主要因の特定

#### 主要因1: 季節要因 (寄与度: 45%)
- **説明**: 夏季の売上減少傾向
- **根拠**: 過去3年間のデータ

#### 主要因2: 競合参入 (寄与度: 35%)
- **説明**: 新規競合の市場参入
- **根拠**: 市場シェアの変動

### 根本原因分析（5 Whys）
1. なぜ？ → 売上が減少した
2. なぜ？ → 顧客が離脱した
3. なぜ？ → 競合製品に移行した

**根本原因**: 競合製品との差別化不足

### 推奨アクション
1. **短期**: 価格施策の見直し
2. **中期**: 製品改良
3. **長期**: 新製品開発

[FILES: sales_data.csv, market_analysis.md]
"""
    mock_client.models.generate_content.return_value = mock_response
    
    agent = AnalysisAgent(client=mock_client)
    
    state = create_initial_state(
        user_prompt="売上が下がった原因は？",
        display_label="売上が下がった原因は？",
        company="テスト社",
        company_folder="test",
    )
    
    result = agent.run(state)
    
    print(f"応答テキスト長: {len(result['agent_result']['response_text'])} 文字")
    print(f"抽出ファイル: {result['agent_result']['files']}")
    
    assert "agent_result" in result
    assert "要因分析" in result["agent_result"]["response_text"]
    assert "sales_data.csv" in result["agent_result"]["files"]
    
    print("✅ テスト5 成功: AnalysisAgent が正しく実行されました")


def test_base_agent_file_extraction():
    """BaseAgent の [FILES:] タグ抽出機能"""
    print("\n" + "=" * 60)
    print("テスト6: BaseAgent のファイル抽出機能")
    print("=" * 60)
    
    from orchestration.agents.base_agent import BaseAgent
    
    # 抽象クラスなのでサブクラスを作成
    class TestAgent(BaseAgent):
        @property
        def agent_name(self):
            return "TestAgent"
        
        def build_system_prompt(self, state):
            return "test prompt"
    
    mock_client = Mock()
    agent = TestAgent(client=mock_client)
    
    # テストケース
    test_cases = [
        ("[FILES: file1.csv, file2.md]", ["file1.csv", "file2.md"]),
        ("[FILE: single.txt]", ["single.txt"]),
        ("No files here", []),
        ("[FILES: a.csv][FILES: b.csv]", ["a.csv", "b.csv"]),
    ]
    
    for text, expected in test_cases:
        result = agent._extract_files(text)
        print(f"  入力: {text[:30]}... → {result}")
        assert result == expected, f"Expected {expected}, got {result}"
    
    print("✅ テスト6 成功: ファイル抽出が正しく動作しています")


def run_all_tests():
    """すべてのテストを実行"""
    print("\n" + "=" * 60)
    print("🧪 エージェント単体テスト開始")
    print("=" * 60)
    
    try:
        test_analysis_agent_prompt()
        test_comparison_agent_prompt()
        test_forecast_agent_prompt()
        test_general_agent_prompt()
        test_analysis_agent_run_with_mock()
        test_base_agent_file_extraction()
        
        print("\n" + "=" * 60)
        print("🎉 すべてのエージェントテストが成功しました！（6/6）")
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
