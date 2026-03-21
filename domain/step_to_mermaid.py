"""
domain/step_to_mermaid.py — 手順テキストからMermaidフローチャートへの自動変換

C08準拠: LLMに出力形式を委ねず、コード側で解析・変換する。
Geminiの回答テキストから番号付きステップを検出し、Mermaidコードに変換する。
"""
from __future__ import annotations

import re
import logging
from typing import Any

logger = logging.getLogger(__name__)

# 手順系キーワード（質問または回答に含まれている場合にフローチャート生成を検討）
_STEP_KEYWORDS = re.compile(
    r"手順|ステップ|フロー|プロセス|流れ|段階|工程|手続き|進め方|やり方|順番|順序"
)

# 番号付き・アルファベットリストのパターン
# "1. xxx" / "A. xxx" / "A: xxx" / "* **A: xxx**" / "- A. xxx" など
_RE_NUMBERED_ITEM = re.compile(
    r"^\s*(?:[*\-]\s+)?(?:\*\*)?(?:\d+|[A-Za-z])[.．)）:：]\s*[*＊]*\s*(.+?)$",
    re.MULTILINE,
)


def _clean_step_label(content: str) -> str:
    """ステップ内容をMermaid用のラベルにクリーンアップする。"""
    clean = re.sub(r"\*\*|__", "", content).strip()
    # コロン以降は説明文なので切り捨て（タイトル部分だけ残す）
    clean = re.split(r"[:：—–\-]", clean)[0].strip()
    # Mermaid互換: 括弧・特殊文字を除去
    clean = clean.replace("（", "").replace("）", "")
    clean = clean.replace("(", "").replace(")", "")
    clean = clean.replace('"', "").replace("'", "")
    clean = clean.replace("#", "").replace(";", "")
    # 長すぎる場合は切り詰め
    if len(clean) > 30:
        clean = clean[:27] + "..."
    return clean


def detect_steps(text: str) -> list[str]:
    """回答テキストから最も項目数が多い番号付きリストを抽出する。"""
    groups = detect_all_step_groups(text)
    if not groups:
        return []
    best = max(groups, key=lambda g: len(g[2]))
    return best[2]


def detect_all_step_groups(text: str) -> list[tuple[int, int, list[str]]]:
    """回答テキストから3項目以上の全リストグループを検出する。

    Returns:
        [(start_line, end_line, [step_labels]), ...] のリスト
    """
    lines = text.split("\n")
    groups: list[tuple[int, int, list[str]]] = []
    current_labels: list[str] = []
    group_start = -1

    for i, line in enumerate(lines):
        m = _RE_NUMBERED_ITEM.match(line)
        if m:
            if group_start < 0:
                group_start = i
            current_labels.append(m.group(1))
        else:
            if current_labels:
                steps = [_clean_step_label(c) for c in current_labels]
                steps = [s for s in steps if s]
                if len(steps) >= 3:
                    groups.append((group_start, i, steps[:10]))
                current_labels = []
                group_start = -1
    # 末尾処理
    if current_labels:
        steps = [_clean_step_label(c) for c in current_labels]
        steps = [s for s in steps if s]
        if len(steps) >= 3:
            groups.append((group_start, len(lines), steps[:10]))

    return groups


def should_generate_flowchart(question: str, answer: str) -> bool:
    """フローチャートを生成すべきかどうか判定する。

    条件:
    1. 質問または回答に手順系キーワードが含まれる
    2. 回答に番号付きリストが3項目以上ある
    """
    has_keyword = bool(_STEP_KEYWORDS.search(question))
    steps = detect_steps(answer)
    return has_keyword and len(steps) >= 3


def steps_to_mermaid(steps: list[str]) -> str:
    """ステップのリストからMermaidフローチャートコードを生成する。"""
    if len(steps) < 3:
        return ""

    lines = ["graph TD"]
    for i, step in enumerate(steps):
        node_id = chr(65 + i) if i < 26 else f"N{i}"
        # Mermaid用にダブルクォートをエスケープ
        safe_step = step.replace('"', "'")
        lines.append(f'    {node_id}["{safe_step}"]')

    # 矢印で接続
    for i in range(len(steps) - 1):
        src = chr(65 + i) if i < 26 else f"N{i}"
        dst = chr(65 + i + 1) if i + 1 < 26 else f"N{i+1}"
        lines.append(f"    {src} --> {dst}")

    return "\n".join(lines)


def maybe_generate_mermaid_segment(question: str, answer: str) -> dict[str, Any] | None:
    """質問と回答を受け取り、フローチャートセグメントを生成する（後方互換）。"""
    segments = maybe_generate_mermaid_segments(question, answer)
    return segments[0] if segments else None


def maybe_generate_mermaid_segments(question: str, answer: str) -> list[dict[str, Any]]:
    """質問と回答を受け取り、全リストグループのフローチャートセグメントを生成する。

    生成不要の場合は空リストを返す。
    """
    if not should_generate_flowchart(question, answer):
        return []

    groups = detect_all_step_groups(answer)
    if not groups:
        return []

    results = []
    for _start, _end, steps in groups:
        code = steps_to_mermaid(steps)
        if code:
            logger.info("[StepToMermaid] Generated flowchart with %d steps", len(steps))
            results.append({
                "type": "viz",
                "chart_type": "mermaid",
                "title": "",
                "code": code,
            })

    return results


def inject_mermaid_into_segments(segments: list[dict[str, Any]], mermaid_seg: dict[str, Any]) -> list[dict[str, Any]]:
    """後方互換: 単一セグメントを挿入する。"""
    return inject_all_mermaids_into_segments(segments, [mermaid_seg])


def inject_all_mermaids_into_segments(segments: list[dict[str, Any]], mermaid_segs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """全てのMermaidセグメントを、対応するリストの直後に挿入する。

    各テキストセグメント内のリストグループを検出し、
    3項目以上のグループ直後にMermaidセグメントを1つずつ挿入する。
    """
    if not mermaid_segs:
        return segments

    # 全テキストセグメント内のリストグループを収集
    # (segment_idx, split_line, group_size) のリスト
    all_groups: list[tuple[int, int, int]] = []

    for idx, seg in enumerate(segments):
        if seg.get("type") != "text":
            continue
        content = seg.get("content", "")
        lines = content.split("\n")

        group_start = -1
        for li, line in enumerate(lines):
            if _RE_NUMBERED_ITEM.match(line):
                if group_start < 0:
                    group_start = li
            else:
                if group_start >= 0:
                    count = li - group_start
                    if count >= 3:
                        all_groups.append((idx, li, count))
                    group_start = -1
        if group_start >= 0:
            count = len(lines) - group_start
            if count >= 3:
                all_groups.append((idx, len(lines), count))

    # サイズ降順でソートし、mermaid_segsと1対1で対応させる
    all_groups.sort(key=lambda x: x[2], reverse=True)

    # 挿入対象を決定（mermaid_segsの数だけ）
    inserts = list(zip(all_groups, mermaid_segs))

    if not inserts:
        segments.extend(mermaid_segs)
        return segments

    # 後方から挿入（インデックスがずれないように）
    # まずsegment_idx, split_lineでソート（後方から処理するため逆順）
    inserts.sort(key=lambda x: (x[0][0], x[0][1]), reverse=True)

    for (seg_idx, split_line, _count), m_seg in inserts:
        content = segments[seg_idx].get("content", "")
        lines = content.split("\n")
        before_text = "\n".join(lines[:split_line]).strip()
        after_text = "\n".join(lines[split_line:]).strip()

        replacement = []
        if before_text:
            replacement.append({"type": "text", "content": before_text})
        replacement.append(m_seg)
        if after_text:
            replacement.append({"type": "text", "content": after_text})

        segments = segments[:seg_idx] + replacement + segments[seg_idx + 1:]

    return segments
