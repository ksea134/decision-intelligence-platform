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

    return normalized
