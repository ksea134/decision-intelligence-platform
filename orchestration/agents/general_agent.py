"""
orchestration/agents/general_agent.py — 汎用エージェント

【役割】
特定の分析パターンに該当しない一般的な質問に対応する。
現行の ReasoningEngine と同等の汎用的な回答を提供する。

【特徴】
- 幅広い質問に対応
- データに基づく回答
- 分かりやすい構成
- 適切な参照表示
"""
from __future__ import annotations

from orchestration.agents.base_agent import BaseAgent, build_data_context_section
from orchestration.graph.state import WorkflowState


# -----------------------------------------------------------------------------
# システムプロンプト
# -----------------------------------------------------------------------------
GENERAL_SYSTEM_PROMPT = """あなたは{company}の意思決定を支援するトップコンサルタントです。
ユーザーの質問に対して、的確で分かりやすい回答を提供してください。

## あなたの役割
- ユーザーの質問を正確に理解する
- 利用可能なデータを活用して回答する
- 分かりやすく構造化された回答を提供する
- 追加で検討すべき観点があれば提示する

## 回答の原則

### 構成
1. **結論を先に**: 最も重要な回答を冒頭に
2. **根拠を示す**: データや事実に基づく説明
3. **詳細を補足**: 必要に応じて追加情報
4. **次のステップ**: 追加で検討すべき点があれば提示

### 表現
- 簡潔で分かりやすい日本語
- 専門用語は必要に応じて説明を加える
- 数値は具体的に示す
- 不確実な情報は「〜と推定される」「〜の可能性がある」と明示

## 回答フォーマット

質問の種類に応じて適切な形式で回答してください：

### 事実確認の質問
- 結論を明確に述べる
- 根拠となるデータを示す
- 補足情報があれば追加

### 説明を求める質問
- 概要を最初に
- 詳細を段階的に説明
- 具体例があれば提示

### 推奨を求める質問
- 推奨事項を明確に
- 理由を説明
- 代替案があれば提示

### 共通ルール
- 回答の最後に参照したファイルを明記
- [FILES: ファイル名1, ファイル名2] の形式で記載

## データコンテキスト
{data_context}

## 言語ルール
- ユーザーの言語に合わせて回答してください
- 丁寧で親しみやすいトーン
- 長すぎず、必要十分な長さで回答
"""


# -----------------------------------------------------------------------------
# GeneralAgent クラス
# -----------------------------------------------------------------------------
class GeneralAgent(BaseAgent):
    """
    汎用エージェント。
    
    特定の分析パターンに該当しない質問に対して、
    汎用的な回答を提供する。
    """
    
    @property
    def agent_name(self) -> str:
        return "GeneralAgent"
    
    def build_system_prompt(self, state: WorkflowState) -> str:
        """汎用回答用のシステムプロンプトを構築する"""
        company = state.get("company", "お客様企業")
        data_context = build_data_context_section(state)
        
        return GENERAL_SYSTEM_PROMPT.format(
            company=company,
            data_context=data_context if data_context else "（データなし）",
        )


# -----------------------------------------------------------------------------
# ファクトリ関数
# -----------------------------------------------------------------------------
def create_general_agent(client, model: str = None, temperature: float = 0.0):
    """
    GeneralAgent のインスタンスを生成する。
    
    Args:
        client: Gemini API クライアント
        model: 使用するモデル名（デフォルト: gemini-1.5-pro）
        temperature: 生成温度
    
    Returns:
        GeneralAgent インスタンス
    """
    from orchestration.agents.base_agent import MAIN_MODEL
    return GeneralAgent(
        client=client,
        model=model or MAIN_MODEL,
        temperature=temperature,
    )
