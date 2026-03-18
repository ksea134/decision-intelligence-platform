"""
domain/sql_validator.py — SQLバリデーション（セキュリティ）

【役割】
LLMが生成したSQLが安全かどうかを検査する。
危険な命令（DELETE, DROP等13種）を含むSQLを例外で拒否する。

【設計原則】
- 完全にフレームワーク非依存。
- UIに依存しない。検証失敗は例外（SQLValidationError）で返す。
- 純粋な関数として実装。副作用なし。

【現行コードからの継承】
- validate_sql() のロジックをそのまま継承（セキュリティ仕様は変更なし）
- st.warning() の直接呼び出しを除去（UIへの依存を排除）
"""

from __future__ import annotations
import re
from typing import Final

# 日本語文字（CJK統合漢字・ひらがな・カタカナ）を含むトークンを検出する正規表現
_CJK_TOKEN_RE = re.compile(
    r"(?<!`)("                          # バッククォートの直後でない
    r"[A-Za-z0-9_]*"                    # 先頭に英数字があってもよい
    r"[\u3000-\u9FFF\uF900-\uFAFF]"     # 日本語文字を1文字以上含む
    r"[A-Za-z0-9_\u3000-\u9FFF\uF900-\uFAFF]*"  # 続き
    r")(?!`)"                           # バッククォートの直前でない
)


def auto_backtick_japanese(sql: str) -> str:
    """
    SQL中のバッククォートで囲まれていない日本語識別子を自動的に
    バッククォートで囲む。

    例: SUM(合計) → SUM(`合計`)
        SELECT 月, A事業部門 → SELECT `月`, `A事業部門`

    文字列リテラル（'...' / "..."）やバッククォート内はそのまま保持する。
    """
    # SQLをセグメントに分割: (テキスト, 保護対象) のペアで管理
    segments: list[tuple[str, bool]] = []  # (text, is_protected)
    i = 0
    current: list[str] = []

    while i < len(sql):
        ch = sql[i]
        # バッククォート: 中身は保護
        if ch == '`':
            if current:
                segments.append(("".join(current), False))
                current = []
            j = i + 1
            while j < len(sql) and sql[j] != '`':
                j += 1
            segments.append((sql[i:j + 1], True))
            i = j + 1
            continue
        # 文字列リテラル: 中身は保護
        if ch in ("'", '"'):
            if current:
                segments.append(("".join(current), False))
                current = []
            quote = ch
            j = i + 1
            while j < len(sql) and sql[j] != quote:
                j += 1
            segments.append((sql[i:j + 1], True))
            i = j + 1
            continue
        current.append(ch)
        i += 1

    if current:
        segments.append(("".join(current), False))

    # 保護されていないセグメントのみ正規表現でバッククォート付与
    result_parts: list[str] = []
    for text, is_protected in segments:
        if is_protected:
            result_parts.append(text)
        else:
            result_parts.append(_CJK_TOKEN_RE.sub(r"`\1`", text))

    return "".join(result_parts)


SQL_DISALLOWED_KEYWORDS: Final[frozenset[str]] = frozenset({
    "INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE",
    "TRUNCATE", "REPLACE", "MERGE", "GRANT", "REVOKE",
    "CALL", "EXEC", "EXECUTE",
})


class SQLValidationError(Exception):
    """SQLバリデーション失敗を表す例外。"""
    pass


def validate_sql(sql: str) -> str:
    """
    SQLが安全かどうかを検査し、安全であれば正規化したSQLを返す。

    以下の条件をすべて満たす場合のみ通過する：
    1. 空でないこと
    2. SELECT または WITH で始まること
    3. 禁止キーワード（13種）を含まないこと
    4. セミコロンによる複文実行でないこと（文字列リテラル内は除く）

    Args:
        sql: 検査対象のSQL文字列。

    Returns:
        正規化済みのSQL文字列（末尾のセミコロン・空白を除去）。

    Raises:
        SQLValidationError: 検査に失敗した場合。
    """
    normalized = sql.strip().rstrip(";").strip()

    if not normalized:
        raise SQLValidationError("空のSQLは実行できません。")

    without_comments = re.sub(r"--[^\n]*", "", normalized)
    without_comments = re.sub(r"/\*.*?\*/", "", without_comments, flags=re.DOTALL)
    tokens = without_comments.upper().split()

    if not tokens:
        raise SQLValidationError("空のSQLは実行できません。")

    if tokens[0] not in ("SELECT", "WITH"):
        raise SQLValidationError(
            f"SELECT / WITH 文のみ許可されています（検出: {tokens[0]}）。"
        )

    found = SQL_DISALLOWED_KEYWORDS.intersection(tokens)
    if found:
        raise SQLValidationError(
            f"禁止されたSQL操作が含まれています: {', '.join(sorted(found))}"
        )

    in_single = False
    in_double = False
    for ch in normalized:
        if ch == "'" and not in_double:
            in_single = not in_single
        elif ch == '"' and not in_single:
            in_double = not in_double
        elif ch == ";" and not in_single and not in_double:
            raise SQLValidationError("複数のSQL文は実行できません。")

    normalized = auto_backtick_japanese(normalized)

    return normalized
