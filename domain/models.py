"""
domain/models.py — データモデル定義

【役割】
システム全体で使うデータの「型（形）」を定義する。

【設計原則】
- 完全にフレームワーク非依存。StreamlitもGCPも一切importしない。
- frozen=True（不変）で定義する。値の意図せぬ書き換えを防ぐ。

【現行コードからの変更点】
- viz_data フィールド → 削除（インフォグラフィックで代替済み）
- SupplementBundle クラス → 削除（未使用）
- RenderContext → UI層に移動
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Any, TypedDict
import pandas as pd


@dataclass(frozen=True)
class CloudDataResult:
    """BigQueryまたはGCSへの接続結果。"""
    content: str
    is_connected: bool
    error_type: str = ""
    error_detail: str = ""

    @property
    def is_error(self) -> bool:
        return not self.is_connected

    @property
    def status_label(self) -> str:
        if self.is_connected:
            return "接続済み"
        if self.error_type:
            return f"接続エラー（{self.error_type}）"
        return "未接続"

    @property
    def recovery_hint(self) -> str:
        hints = {
            "auth":      "サービスアカウントの権限・認証情報を確認してください。",
            "not_found": "リソース名（Dataset / Bucket）が正しいか確認してください。",
            "network":   "ネットワーク接続を確認してください。VPC Service Controls の設定も確認してください。",
            "config":    "GCP Project ID・Bucket名の設定を確認してください。",
        }
        return hints.get(self.error_type, "クラウド接続設定を確認してください。")


@dataclass(frozen=True)
class SQLResult:
    """BigQueryのSQL実行結果。"""
    columns: list[str]
    data: dict[str, list[Any]]
    row_count: int

    def to_dataframe(self) -> pd.DataFrame:
        return pd.DataFrame(self.data, columns=self.columns)


@dataclass(frozen=True)
class LoadedDirectory:
    """1ディレクトリの読込結果。"""
    content: str
    files: list[str]


@dataclass(frozen=True)
class CompanyAssets:
    """企業1社分のデータ一式。"""
    intro_text: str
    prompt_text: str
    prompt_files: list[str]
    knowledge_text: str
    knowledge_files: list[str]
    structured_text: str
    structured_files: list[str]
    unstructured_text: str
    unstructured_files: list[str]
    smart_cards: list[dict[str, Any]]
    dirs: dict[str, str]


@dataclass(frozen=True)
class ParsedResponse:
    """Gemini出力の解析結果。"""
    display_text: str
    files: list[str]
    sql: str | None


class MessageArtifacts(TypedDict, total=False):
    """回答に付随する生成物。"""
    info_html: str
    info_data: dict
    deepdive: list[str]
    generating_info: bool
    generating_dd: bool


class ChatMessage(TypedDict, total=False):
    """チャットの1メッセージ。viz_dataは削除済み。"""
    role: str
    content: str
    llm_prompt: str
    files: list[str]
    thought_process: str
    sql_result: dict[str, Any] | None
    sql_query: str
    artifacts: MessageArtifacts
