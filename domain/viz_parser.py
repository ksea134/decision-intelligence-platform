"""
domain/viz_parser.py — InlineViz タグパーサー

LLMの回答テキストから <viz> タグを検出し、
テキストセグメントとチャートセグメントに分割する。

セグメント形式:
  {"type": "text", "content": "テキスト内容"}
  {"type": "viz", "chart_type": "bar", "title": "タイトル", "labels": [...], "data": [...]}
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

_RE_VIZ_TAG = re.compile(
    r'<viz\s+type="(bar|line|pie|flowchart)"\s+title="([^"]*)">\s*'
    r'(\{.*?\})\s*'
    r'</viz>',
    re.DOTALL,
)


def parse_viz_segments(text: str) -> list[dict[str, Any]]:
    """
    テキストを <viz> タグ境界で分割し、セグメントのリストを返す。

    Args:
        text: LLMの回答テキスト（<viz>タグを含む可能性がある）

    Returns:
        セグメントのリスト。各要素は以下のいずれか:
        - {"type": "text", "content": "..."}
        - {"type": "viz", "chart_type": "bar", "title": "...", "labels": [...], "data": [...]}
    """
    segments: list[dict[str, Any]] = []
    last_end = 0

    for match in _RE_VIZ_TAG.finditer(text):
        # マッチ前のテキスト
        before = text[last_end:match.start()].strip()
        if before:
            segments.append({"type": "text", "content": before})

        # チャートデータのパース
        chart_type = match.group(1)
        title = match.group(2)
        json_str = match.group(3)

        try:
            data = json.loads(json_str)
            labels = data.get("labels", [])
            values = data.get("data", [])
            if labels and values and len(labels) == len(values):
                segments.append({
                    "type": "viz",
                    "chart_type": chart_type,
                    "title": title,
                    "labels": labels,
                    "data": values,
                })
            else:
                logger.warning("[VizParser] labels/data mismatch: labels=%d, data=%d", len(labels), len(values))
                # パース失敗時はタグごとテキストとして扱う
                segments.append({"type": "text", "content": match.group(0)})
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning("[VizParser] JSON parse error: %s", e)
            segments.append({"type": "text", "content": match.group(0)})

        last_end = match.end()

    # 最後のテキスト
    remaining = text[last_end:].strip()
    if remaining:
        segments.append({"type": "text", "content": remaining})

    # <viz>タグが一つもなかった場合
    if not segments and text.strip():
        segments.append({"type": "text", "content": text.strip()})

    return segments
