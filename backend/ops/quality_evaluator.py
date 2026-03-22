"""
backend/ops/quality_evaluator.py — AI回答品質評価エンジン

回答を5項目で自動評価する。
- ルールベース: 出典の有無、回答長、データ参照（モデル非依存）
- LLM評価: 一貫性（回答を生成したモデルと同じモデルで評価 — バイアス回避）
- フィードバック: 👍👎データから算出

C08準拠: LLM評価は数値のみを返す明確な指示。フォールバックあり。
"""
from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


def evaluate_response(
    question: str,
    answer: str,
    sources: list[str],
    model_id: str = "",
) -> dict[str, Any]:
    """回答を5項目で評価する。

    Args:
        question: ユーザーの質問文
        answer: AIの回答テキスト
        sources: 参照したデータソース一覧（["BQ:table", "GCS:file"]等）
        model_id: 回答を生成したモデルID（一貫性評価で使用）

    Returns:
        {
            "citation_score": 0〜100,
            "length_score": 0〜100,
            "data_ref_score": 0〜100,
            "coherence_score": 0〜100 or -1（評価失敗）,
            "overall_score": 0〜100,
        }
    """
    scores = {
        "citation_score": _evaluate_citations(answer),
        "length_score": _evaluate_length(answer),
        "data_ref_score": _evaluate_data_references(answer, sources),
        "coherence_score": _evaluate_coherence(question, answer, model_id),
    }

    # 全体スコア（加重平均、coherence_scoreが-1の場合は除外）
    valid_scores = {k: v for k, v in scores.items() if v >= 0}
    if valid_scores:
        weights = {
            "citation_score": 0.25,
            "length_score": 0.15,
            "data_ref_score": 0.25,
            "coherence_score": 0.35,
        }
        total_weight = sum(weights[k] for k in valid_scores)
        scores["overall_score"] = round(
            sum(v * weights[k] / total_weight for k, v in valid_scores.items())
        )
    else:
        scores["overall_score"] = -1

    return scores


def _evaluate_citations(answer: str) -> int:
    """出典の有無を評価する。※1、※2等の米印出典があるか。"""
    citation_pattern = re.compile(r"※\d+")
    citations = citation_pattern.findall(answer)
    if len(citations) >= 2:
        return 100
    elif len(citations) == 1:
        return 50
    return 0


def _evaluate_length(answer: str) -> int:
    """回答長を評価する。短すぎ・長すぎを減点。"""
    length = len(answer)
    if length < 50:
        return 10  # 極端に短い
    elif length < 200:
        return 50  # やや短い
    elif length <= 3000:
        return 100  # 適切
    elif length <= 5000:
        return 80  # やや長い
    return 60  # 長すぎ


def _evaluate_data_references(answer: str, sources: list[str]) -> int:
    """データソースの参照を評価する。"""
    if not sources:
        # 回答にBQ:やGCS:の言及があるか
        has_bq = "BQ:" in answer or "BigQuery" in answer
        has_gcs = "GCS:" in answer
        if has_bq or has_gcs:
            return 70
        return 0

    # sourcesにBQまたはGCSのデータが含まれているか
    has_bq = any(s.startswith("BQ:") for s in sources)
    has_gcs = any(s.startswith("GCS:") for s in sources)
    if has_bq and has_gcs:
        return 100
    elif has_bq or has_gcs:
        return 80
    return 30


def _evaluate_coherence(question: str, answer: str, model_id: str) -> int:
    """一貫性を評価する。回答を生成したモデルと同じモデルで採点（バイアス回避）。"""
    if not model_id or not question or not answer:
        return -1  # 評価不可

    try:
        from orchestration.llm_client import generate_text

        prompt = (
            "以下の質問と回答の品質を0〜100の数値で評価してください。\n"
            "評価基準:\n"
            "- 質問に対して的確に答えているか\n"
            "- 根拠となるデータを示しているか\n"
            "- 構造が明確か（結論→根拠→詳細）\n"
            "- 意思決定に役立つ情報を提供しているか\n\n"
            f"【質問】\n{question[:500]}\n\n"
            f"【回答】\n{answer[:2000]}\n\n"
            "数値のみを出力してください（例: 85）。説明は不要です。"
        )

        result = generate_text(
            model=model_id,
            contents=prompt,
            temperature=0.0,
        )

        # 数値を抽出
        numbers = re.findall(r"\d+", result.strip())
        if numbers:
            score = int(numbers[0])
            return max(0, min(100, score))

        logger.warning("[QualityEval] Coherence: no number in response: %s", result[:50])
        return -1

    except Exception as e:
        logger.warning("[QualityEval] Coherence evaluation failed: %s", e)
        return -1
