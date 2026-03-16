#!/usr/bin/env python3
"""Phase 1 簡易動作確認スクリプト"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dataclasses import dataclass

@dataclass
class MockCloudDataResult:
    content: str = ""
    is_connected: bool = False

@dataclass
class MockAssets:
    knowledge_text: str = "テスト企業は製造業です。"
    prompt_text: str = ""
    structured_text: str = "売上: Q1=100億, Q2=95億, Q3=88億"
    unstructured_text: str = ""

@dataclass
class MockDataContext:
    bq_result: MockCloudDataResult = None
    gcs_result: MockCloudDataResult = None
    assets: MockAssets = None
    bq_connected: bool = False
    def __post_init__(self):
        self.bq_result = self.bq_result or MockCloudDataResult()
        self.gcs_result = self.gcs_result or MockCloudDataResult()
        self.assets = self.assets or MockAssets()

@dataclass
class MockCloudConfig:
    folder_name: str = "test"

def main():
    print("=" * 60)
    print("🔍 環境チェック")
    print("=" * 60)
    
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("❌ GEMINI_API_KEY が未設定")
        return
    print(f"✅ GEMINI_API_KEY: {api_key[:15]}...")
    
    try:
        import langgraph
        print("✅ langgraph: installed")
    except ImportError:
        print("❌ langgraph がない"); return
    
    from google import genai
    print("✅ google-genai: installed")
    
    from orchestration.reasoning_engine_v2 import ReasoningEngineV2
    print("✅ ReasoningEngineV2: imported")
    
    print("\n" + "=" * 60)
    print("🧪 エージェントルーティングテスト")
    print("=" * 60)
    
    client = genai.Client(api_key=api_key)
    engine = ReasoningEngineV2(client=client, data_agent=None, memory=None,
                                use_llm_router=True, use_llm_agents=False)
    
    tests = [
        ("売上が下がった原因は？", "analysis"),
        ("AとBを比較して", "comparison"),
        ("来月の予測は？", "forecast"),
        ("会社概要を教えて", "general"),
    ]
    
    for prompt, expected in tests:
        result = engine.run(prompt, prompt, "テスト社", MockCloudConfig(), MockDataContext())
        actual = result.agent_type if result else "N/A"
        status = "✅" if actual == expected else "⚠️"
        print(f"{status} '{prompt}' → {actual} (期待: {expected})")
    
    print("\n🎉 テスト完了！")

if __name__ == "__main__":
    main()
