"""
orchestration/agents/router_agent.py — 意図分類エージェント（Router）

【役割】
ユーザーの質問を分析し、最適なエージェントを選択する。
Gemini Flash を使用して高速かつ高精度な分類を行う。

【設計原則】
- Gemini 1.5 Flash を使用（高速・低コスト）
- JSON モードで構造化出力を強制
- エラー時はキーワードベースにフォールバック
- DI パターンで Client を注入（テスト容易性）

【修正履歴】
- 2026-03-16: google-genai をオプションインポートに変更（テスト環境対応）
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any, TYPE_CHECKING

# google-genai はオプション依存（テスト環境ではモックを使用）
try:
    from google import genai
    from google.genai import types
    GENAI_AVAILABLE = True
except ImportError:
    genai = None  # type: ignore
    types = None  # type: ignore
    GENAI_AVAILABLE = False

from orchestration.graph.state import ClassificationResult, IntentType

logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# 定数
# -----------------------------------------------------------------------------
# 使用するモデル（Flash は Pro より 3〜5 倍高速）
ROUTER_MODEL = "gemini-2.5-flash"

# 分類用プロンプト
ROUTER_SYSTEM_PROMPT = """あなたは質問の意図を分類するAIアシスタントです。
ユーザーの質問を分析し、最適なカテゴリを選択してください。

## 分類カテゴリ

### analysis（要因分析）
原因・理由・要因を問う質問。「なぜ？」「どうして？」「原因は？」など。
例:
- 「売上が下がった原因は何ですか？」
- 「なぜ利益率が低下しているのでしょうか」
- 「顧客離脱の要因を教えてください」
- 「この問題の根本原因は何だと思いますか」

### comparison（比較）
2つ以上の対象を比較・対照する質問。
例:
- 「A製品とB製品の売上を比較してください」
- 「昨年と今年の違いは？」
- 「競合他社と比べて当社の強みは？」
- 「どちらが優れていますか」

### forecast（予測）
将来・今後の見通しを問う質問。
例:
- 「来月の売上予測は？」
- 「今後のトレンドはどうなりますか」
- 「年度末の着地見込みを教えてください」
- 「このまま続くとどうなりますか」

### general（汎用）
上記のいずれにも該当しない一般的な質問。
例:
- 「会社の概要を教えてください」
- 「最新のデータを見せてください」
- 「○○について説明してください」
- 「このレポートを要約してください」

## 出力形式
必ず以下のJSON形式で回答してください。それ以外のテキストは含めないでください。

{
  "intent": "analysis|comparison|forecast|general",
  "confidence": 0.0〜1.0の数値,
  "reasoning": "分類理由の簡潔な説明（日本語）",
  "entities": ["抽出したキーワードのリスト"]
}

## 注意事項
- 複数の意図が混在する場合は、最も強い意図を選択してください
- 判断が難しい場合は confidence を低くし、general を選択してください
- entities には質問から抽出した重要なキーワードを含めてください
"""


# -----------------------------------------------------------------------------
# Router Agent クラス
# -----------------------------------------------------------------------------
class RouterAgent:
    """
    意図分類エージェント。
    
    ユーザーの質問を Gemini Flash で分析し、適切なエージェントを決定する。
    
    Attributes:
        _client: Gemini API クライアント
        _model: 使用するモデル名
        _fallback_enabled: LLM エラー時のフォールバックを有効にするか
    """
    
    def __init__(
        self,
        client: genai.Client,
        model: str = ROUTER_MODEL,
        fallback_enabled: bool = True,
    ) -> None:
        """
        RouterAgent を初期化する。
        
        Args:
            client: Gemini API クライアント（DI パターン）
            model: 使用するモデル名
            fallback_enabled: LLM エラー時にキーワードベースにフォールバックするか
        """
        self._client = client
        self._model = model
        self._fallback_enabled = fallback_enabled
    
    def classify(self, user_prompt: str) -> ClassificationResult:
        """
        ユーザーの質問を分類する。
        
        Args:
            user_prompt: ユーザーの質問テキスト
        
        Returns:
            ClassificationResult: 分類結果
        """
        if not user_prompt or not user_prompt.strip():
            logger.warning("[Router] Empty prompt, returning general")
            return self._create_result("general", 0.5, "空の質問", [])
        
        try:
            return self._classify_with_llm(user_prompt)
        except Exception as e:
            logger.error("[Router] LLM classification failed: %s", e)
            if self._fallback_enabled:
                logger.info("[Router] Falling back to keyword-based classification")
                return self._classify_with_keywords(user_prompt)
            raise
    
    def _classify_with_llm(self, user_prompt: str) -> ClassificationResult:
        """
        Gemini Flash を使用して分類する。
        
        Args:
            user_prompt: ユーザーの質問テキスト
        
        Returns:
            ClassificationResult: 分類結果
        """
        # config を作成（types が利用可能な場合は GenerateContentConfig を使用）
        config_dict = {
            "system_instruction": ROUTER_SYSTEM_PROMPT,
            "temperature": 0.0,  # 決定論的な分類
            "max_output_tokens": 256,  # 分類のみなので少量で OK
            "response_mime_type": "application/json",  # JSON 出力を強制
        }
        
        if types is not None:
            config = types.GenerateContentConfig(**config_dict)
        else:
            # テスト環境など types が利用できない場合は dict をそのまま使用
            config = config_dict
        
        response = self._client.models.generate_content(
            model=self._model,
            contents=[user_prompt],
            config=config,
        )
        
        # レスポンスのパース
        response_text = response.text.strip()
        logger.debug("[Router] LLM response: %s", response_text)
        
        # JSON をパース
        result = self._parse_json_response(response_text)
        
        intent = result.get("intent", "general")
        if intent not in ("analysis", "comparison", "forecast", "general"):
            logger.warning("[Router] Invalid intent '%s', falling back to general", intent)
            intent = "general"
        
        confidence = float(result.get("confidence", 0.5))
        confidence = max(0.0, min(1.0, confidence))  # 0〜1 にクリップ
        
        reasoning = result.get("reasoning", "")
        entities = result.get("entities", [])
        
        logger.info(
            "[Router] LLM classification: intent=%s, confidence=%.2f, reasoning=%s",
            intent, confidence, reasoning
        )
        
        return self._create_result(intent, confidence, reasoning, entities)
    
    def _parse_json_response(self, response_text: str) -> dict[str, Any]:
        """
        LLM レスポンスから JSON をパースする。
        
        Args:
            response_text: LLM のレスポンステキスト
        
        Returns:
            パースされた辞書
        """
        # そのまま JSON としてパース
        try:
            return json.loads(response_text)
        except json.JSONDecodeError:
            pass
        
        # Markdown コードブロックから抽出
        json_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", response_text)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass
        
        # { } で囲まれた部分を抽出
        brace_match = re.search(r"\{[\s\S]*\}", response_text)
        if brace_match:
            try:
                return json.loads(brace_match.group(0))
            except json.JSONDecodeError:
                pass
        
        logger.warning("[Router] Failed to parse JSON from response: %s", response_text[:100])
        return {}
    
    def _classify_with_keywords(self, user_prompt: str) -> ClassificationResult:
        """
        キーワードベースで分類する（フォールバック用）。
        
        Args:
            user_prompt: ユーザーの質問テキスト
        
        Returns:
            ClassificationResult: 分類結果
        """
        prompt_lower = user_prompt.lower()
        
        # キーワード定義
        analysis_keywords = ["なぜ", "原因", "理由", "要因", "どうして", "why", "cause"]
        comparison_keywords = ["比較", "違い", "差", "vs", "どちらが", "compare", "より", "difference"]
        forecast_keywords = ["予測", "今後", "見通し", "どうなる", "将来", "forecast", "来月", "来年", "見込み"]
        
        # マッチング
        if any(kw in prompt_lower for kw in analysis_keywords):
            matched = [kw for kw in analysis_keywords if kw in prompt_lower]
            return self._create_result(
                "analysis", 0.75, "キーワードベース: 原因・理由を問う表現を検出", matched
            )
        
        if any(kw in prompt_lower for kw in comparison_keywords):
            matched = [kw for kw in comparison_keywords if kw in prompt_lower]
            return self._create_result(
                "comparison", 0.75, "キーワードベース: 比較を求める表現を検出", matched
            )
        
        if any(kw in prompt_lower for kw in forecast_keywords):
            matched = [kw for kw in forecast_keywords if kw in prompt_lower]
            return self._create_result(
                "forecast", 0.75, "キーワードベース: 予測・将来を問う表現を検出", matched
            )
        
        return self._create_result(
            "general", 0.5, "キーワードベース: 特定のパターンに該当せず", []
        )
    
    def _create_result(
        self,
        intent: IntentType,
        confidence: float,
        reasoning: str,
        entities: list[str],
    ) -> ClassificationResult:
        """
        ClassificationResult を生成する。
        
        Args:
            intent: 分類された意図
            confidence: 信頼度
            reasoning: 分類理由
            entities: 抽出されたエンティティ
        
        Returns:
            ClassificationResult
        """
        return ClassificationResult(
            intent=intent,
            confidence=confidence,
            reasoning=reasoning,
            entities=entities,
        )


# -----------------------------------------------------------------------------
# ファクトリ関数（簡易利用用）
# -----------------------------------------------------------------------------
def create_router_agent(client: genai.Client) -> RouterAgent:
    """
    RouterAgent のインスタンスを生成する。
    
    Args:
        client: Gemini API クライアント
    
    Returns:
        RouterAgent インスタンス
    """
    return RouterAgent(client=client)
