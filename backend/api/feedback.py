"""
backend/api/feedback.py — フィードバックAPIエンドポイント

AIの回答に対する👍👎フィードバックを記録する。
記録先: Cloud Logging（構造化ログ）。将来BigQueryシンクで永続化・分析。
"""
from __future__ import annotations

import logging
from fastapi import APIRouter
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["feedback"])


class FeedbackRequest(BaseModel):
    question: str
    answer_preview: str  # 先頭200文字
    company: str
    rating: str  # "good" | "bad"
    comment: str = ""
    engine: str = ""


@router.post("/feedback")
async def post_feedback(req: FeedbackRequest):
    """フィードバックを記録する。"""
    logger.info(
        "[Feedback] rating=%s, company=%s, engine=%s, comment=%s, question=%s",
        req.rating,
        req.company,
        req.engine,
        req.comment[:100] if req.comment else "",
        req.question[:100],
        extra={
            "feedback_rating": req.rating,
            "feedback_company": req.company,
            "feedback_engine": req.engine,
            "feedback_comment": req.comment,
            "feedback_question": req.question[:200],
            "feedback_answer": req.answer_preview[:200],
        },
    )
    return {"status": "ok", "message": "フィードバックを記録しました"}
