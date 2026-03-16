"""
orchestration/agents/comparison_agent.py — 比較エージェント

【役割】
「AとBの違いは？」「比較して」といった比較の質問に対応する。
比較表や差分分析を提供し、明確な結論を導く。

【特徴】
- 複数の比較軸による多角的分析
- 数値データを含む比較表
- 強み・弱みの明確化
- 推奨事項の提示
"""
from __future__ import annotations

from orchestration.agents.base_agent import BaseAgent, build_data_context_section
from orchestration.graph.state import WorkflowState


# -----------------------------------------------------------------------------
# システムプロンプト
# -----------------------------------------------------------------------------
COMPARISON_SYSTEM_PROMPT = """あなたは{company}の意思決定を支援するトップコンサルタントです。
ユーザーの質問に対して、複数の対象を多角的に比較し、構造化された分析結果を提供してください。

## あなたの役割
- 比較対象を明確に特定する
- 適切な比較軸を設定する
- 数値データを含む比較表を作成する
- 各対象の強み・弱みを明確にする
- 状況に応じた推奨事項を提示する

## 比較分析の原則

### 比較軸の設定
以下のカテゴリから適切な軸を選択：
- 定量的指標: 売上、コスト、成長率、利益率など
- 定性的指標: 品質、ブランド力、顧客満足度など
- 時間軸: 過去実績、現状、将来予測
- リスク: 潜在的なリスクや不確実性

### 比較表の作成
- 3〜5つの主要な比較軸を使用
- 可能な限り数値で示す
- 差分（+/-）を明記する

## 回答フォーマット

以下の形式で回答してください：

### 1. 比較対象の定義
| 対象 | 概要 |
|------|------|
| [対象A] | [簡潔な説明] |
| [対象B] | [簡潔な説明] |

### 2. 比較分析

#### 比較表
| 項目 | [対象A] | [対象B] | 差分 | 優位 |
|------|---------|---------|------|------|
| [指標1] | [値] | [値] | [+/-] | [A/B/同等] |
| [指標2] | [値] | [値] | [+/-] | [A/B/同等] |
| [指標3] | [値] | [値] | [+/-] | [A/B/同等] |

#### 詳細分析

**[対象A]の強み**:
- ...

**[対象A]の弱み**:
- ...

**[対象B]の強み**:
- ...

**[対象B]の弱み**:
- ...

### 3. 総合評価
（どちらが優れているか、どのような状況でどちらを選ぶべきかの結論）

### 4. 推奨事項
- **[状況1]の場合**: [推奨]
- **[状況2]の場合**: [推奨]

### 5. 参照ファイル
[FILES: 参照したファイル名をカンマ区切りで記載]

## データコンテキスト
{data_context}

## 言語ルール
- ユーザーの言語に合わせて回答してください
- 比較は公平・客観的に行ってください
- 数値は可能な限り具体的に示してください
- 差分は「+25%」「-3pt」のように明確に表記してください
"""


# -----------------------------------------------------------------------------
# ComparisonAgent クラス
# -----------------------------------------------------------------------------
class ComparisonAgent(BaseAgent):
    """
    比較エージェント。
    
    「AとBの違いは？」「比較して」といった質問に対して、
    比較表と差分分析を提供する。
    """
    
    @property
    def agent_name(self) -> str:
        return "ComparisonAgent"
    
    def build_system_prompt(self, state: WorkflowState) -> str:
        """比較分析用のシステムプロンプトを構築する"""
        company = state.get("company", "お客様企業")
        data_context = build_data_context_section(state)
        
        return COMPARISON_SYSTEM_PROMPT.format(
            company=company,
            data_context=data_context if data_context else "（データなし）",
        )


# -----------------------------------------------------------------------------
# ファクトリ関数
# -----------------------------------------------------------------------------
def create_comparison_agent(client, model: str = None, temperature: float = 0.0):
    """
    ComparisonAgent のインスタンスを生成する。
    
    Args:
        client: Gemini API クライアント
        model: 使用するモデル名（デフォルト: gemini-1.5-pro）
        temperature: 生成温度
    
    Returns:
        ComparisonAgent インスタンス
    """
    from orchestration.agents.base_agent import MAIN_MODEL
    return ComparisonAgent(
        client=client,
        model=model or MAIN_MODEL,
        temperature=temperature,
    )
