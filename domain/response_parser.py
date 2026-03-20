"""
domain/response_parser.py — LLM出力の解析・整形

【役割】
Geminiが返した生のテキストを安全に解析し、3つの要素に分解する。
1. display_text : ユーザーに見せるテキスト（タグ・SQL除去済み）
2. files        : 引用ファイル名のリスト（[FILES:...]タグから抽出）
3. sql          : LLMが生成したSQL文（存在する場合のみ）

【設計原則】
- 完全にフレームワーク非依存。
- 純粋な関数として実装。同じ入力には必ず同じ出力を返す。
- 正規表現の責務を明確に分割する。

【現行コードからの変更点】
- parse_stream_result() を責務ごとに関数分割して再実装
- normalize_answer_markdown() / sanitize_markdown_display() を統合
- ensure_minimum_emphasis_for_display() は廃止（prompts/で制御）
"""

from __future__ import annotations
import os
import re
from domain.models import ParsedResponse

# ============================================================
# 正規表現定数
# ============================================================

# [FILES: ファイル名1, ファイル名2] タグを検出する
_RE_FILES_TAG = re.compile(r"\[FILES?:\s*(.*?)\]", re.IGNORECASE | re.DOTALL)

# SQLコードブロック（```sql ... ```）を検出する
_BQ3 = "`" * 3
_RE_SQL_FENCE = re.compile(_BQ3 + r"(?:sql|SQL)?\s*\n(.*?)\n" + _BQ3, re.DOTALL)
_RE_SQL_BLOCK  = re.compile(_BQ3 + r"(?:sql|SQL)?\s*\n.*?\n" + _BQ3, re.DOTALL)

# 回答本文に漏れ出たSQL・BigQueryタグを除去する
_RE_SQL_PLAIN      = re.compile(r"(?m)^SELECT\b.*?(?=\n\n|\Z)", re.DOTALL)
_RE_BQ_QUERY_REF   = re.compile(r"※[A-Za-z\d]+\s*[：:]\s*\[BigQuery:.*?[;；][)）]\s*", re.DOTALL)
_RE_BQ_TAG         = re.compile(r"\[BigQuery:\s*[^\]]+\]\s*(?:のクエリ結果)?")
_RE_CITATION_LINE  = re.compile(r"(?m)^※[\dA-Za-z]+[：:].+$")

# ファイルパスからファイル名だけを取り出す際に使う
_RE_BRACKETS = re.compile(r"[\[\]]")


# ============================================================
# 公開関数
# ============================================================

def parse_llm_response(full_text: str) -> ParsedResponse:
    """
    GeminiのストリームテキストからParsedResponseを生成する。

    Args:
        full_text: Geminiが出力した生のテキスト全体。

    Returns:
        ParsedResponse: 表示用テキスト・ファイルリスト・SQLを含むオブジェクト。
    """
    files   = _extract_files(full_text)
    sql     = _extract_sql(full_text)
    display = _clean_display_text(full_text)
    return ParsedResponse(display_text=display, files=files, sql=sql)


def normalize_markdown(text: str) -> str:
    """
    Markdownテキストを表示用に正規化する。

    行の結合・改行の正規化・Markdownレンダリングを壊す文字の処理を行う。
    LLMの出力を事後改変（太字の挿入等）は一切行わない。

    Args:
        text: 正規化対象のMarkdown文字列。

    Returns:
        正規化済みのMarkdown文字列。
    """
    if not text:
        return text

    # 改行コードを統一
    result = text.replace("\r\n", "\n").replace("\r", "\n")

    # $ 記号のエスケープ（数式誤認識防止）
    result = re.sub(r"\$(?=[a-zA-Z\\{])", r"\\$", result)
    result = re.sub(r"(?<=[a-zA-Z}])\$", r"\\$", result)

    # 奇数個の ** はMarkdownを壊すので除去
    if result.count("**") % 2 == 1:
        result = result.replace("**", "")

    # 3個以上連続する改行を2個に統一
    result = re.sub(r"\n{3,}", "\n\n", result)

    return result


# ============================================================
# 内部関数（外部から直接呼ばない）
# ============================================================

def _extract_files(text: str) -> list[str]:
    """[FILES: ...] タグからファイル名リストを抽出する。重複除去済み。"""
    all_files: list[str] = []
    for match in _RE_FILES_TAG.finditer(text):
        for item in match.group(1).split(","):
            cleaned = _RE_BRACKETS.sub("", item).strip()
            if cleaned and cleaned != "なし":
                all_files.append(os.path.basename(cleaned))
    # 順序を保ちながら重複除去
    seen: set[str] = set()
    return [f for f in all_files if not (f in seen or seen.add(f))]


def _extract_sql(text: str) -> str | None:
    """SQLコードブロック（```sql ... ```）からSQL文を抽出する。"""
    match = _RE_SQL_FENCE.search(text)
    return match.group(1).strip() if match else None


def _clean_display_text(text: str) -> str:
    """
    表示用テキストを生成する。
    [FILES:]タグ・SQLブロック・BigQueryタグ等を除去する。
    """
    result = _RE_FILES_TAG.sub("", text).strip()
    # tool_codeブロック除去（フェンス付き・なし両対応）
    result = re.sub(r"```tool_code.*?```", "", result, flags=re.DOTALL).strip()
    result = re.sub(r"(?m)^tool_code\s*\n(?:print\(.*?\)\n?)*", "", result).strip()
    result = _RE_SQL_BLOCK.sub("", result).strip()
    result = _RE_SQL_PLAIN.sub("", result).strip()
    result = _RE_BQ_QUERY_REF.sub("", result).strip()
    result = _RE_BQ_TAG.sub("", result).strip()
    # 米印の出典行は本文に残す（F19 Grounding仕様）
    # result = _RE_CITATION_LINE.sub("", result).strip()
    # 括弧内のSELECT文も除去
    result = re.sub(r"[（(]\s*SELECT\b[^)）]*[;；]\s*[)）]", "", result).strip()
    return result
