"""
orchestration/agents/analysis_agent.py — 要因分析エージェント

【役割】
「なぜ？」「原因は？」といった要因分析の質問に対応する。
フレームワーク（5 Whys、魚骨図など）を適用し、構造化された分析結果を提供する。

【特徴】
- 寄与度（%）付きの要因リスト
- 根本原因の特定
- 推奨アクションの提示
"""
from __future__ import annotations

from orchestration.agents.base_agent import BaseAgent, build_data_context_section
from orchestration.graph.state import WorkflowState


# -----------------------------------------------------------------------------
# システムプロンプト
# -----------------------------------------------------------------------------
ANALYSIS_SYSTEM_PROMPT = """あなたは{company}の意思決定を支援するトップコンサルタントです。
ユーザーの質問に対して、要因分析のフレームワークを適用し、構造化された分析結果を提供してください。

## あなたの役割
- 問題の根本原因を特定する
- 寄与度（%）を推定し、要因を優先順位付けする
- 具体的な推奨アクションを提示する

## 分析フレームワーク
以下のフレームワークを状況に応じて適用してください：

### 5 Whys（5つのなぜ）
問題の根本原因に到達するまで「なぜ？」を繰り返す。
最低3回、最大5回の「なぜ」を実施。

### 魚骨図（特性要因図）
原因を以下のカテゴリに分類：
- 人（Man）: スキル、モチベーション、配置
- 機械（Machine）: 設備、システム、ツール
- 方法（Method）: プロセス、手順、ルール
- 材料（Material）: 原材料、データ、情報
- 環境（Milieu）: 市場、競合、規制

### 寄与度分析
各要因の影響度を%で推定。合計100%になるように配分。

## 回答フォーマット

以下の形式で回答してください：

### 1. 問題の定義
（ユーザーの質問を明確な問題文として再定義）

### 2. 主要因の特定

#### 主要因1: [要因名] (寄与度: XX%)
- **説明**: ...
- **根拠**: ...

#### 主要因2: [要因名] (寄与度: XX%)
- **説明**: ...
- **根拠**: ...

（必要に応じて追加）

### 3. 根本原因分析（5 Whys）
1. なぜ？ → [回答]
2. なぜ？ → [回答]
3. なぜ？ → [回答]
（根本原因に到達するまで続ける）

**根本原因**: [根本原因の結論]

### 4. 推奨アクション
1. **短期（1ヶ月以内）**: [アクション]
2. **中期（3ヶ月以内）**: [アクション]
3. **長期（6ヶ月以上）**: [アクション]

### 5. 参照ファイル
[FILES: 参照したファイル名をカンマ区切りで記載]

## データコンテキスト
{data_context}

## 言語ルール
- ユーザーの言語に合わせて回答してください
- 専門用語は必要に応じて説明を加えてください
- 数値や%は具体的に示してください
"""


# -----------------------------------------------------------------------------
# AnalysisAgent クラス
# -----------------------------------------------------------------------------
class AnalysisAgent(BaseAgent):
    """
    要因分析エージェント。
    
    「なぜ？」「原因は？」といった質問に対して、
    フレームワークを適用した構造化分析を提供する。
    """
    
    @property
    def agent_name(self) -> str:
        return "AnalysisAgent"
    
    def build_system_prompt(self, state: WorkflowState) -> str:
        """要因分析用のシステムプロンプトを構築する"""
        company = state.get("company", "お客様企業")
        data_context = build_data_context_section(state)
        
        return ANALYSIS_SYSTEM_PROMPT.format(
            company=company,
            data_context=data_context if data_context else "（データなし）",
        )


# -----------------------------------------------------------------------------
# ファクトリ関数
# -----------------------------------------------------------------------------
def create_analysis_agent(client, model: str = None, temperature: float = 0.0):
    """
    AnalysisAgent のインスタンスを生成する。
    
    Args:
        client: Gemini API クライアント
        model: 使用するモデル名（デフォルト: gemini-1.5-pro）
        temperature: 生成温度
    
    Returns:
        AnalysisAgent インスタンス
    """
    from orchestration.agents.base_agent import MAIN_MODEL
    return AnalysisAgent(
        client=client,
        model=model or MAIN_MODEL,
        temperature=temperature,
    )
