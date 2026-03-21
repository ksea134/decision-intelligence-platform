"""
config/app_config.py — アプリ全体の設定値

【役割】
バージョン・モデル名・キャッシュ時間・文字数上限などの定数を一箇所で管理する。
ここを見れば「このアプリのパラメータ」がすべてわかる状態にする。

【設計原則】
- 完全にフレームワーク非依存。StreamlitもGCPも一切importしない。
- frozen=True（不変）で定義する。実行中に値が変わることを防ぐ。
- UIに関する定数（色・高さ等）はこのファイルに含めない。ui/層で管理する。

【現行コードからの変更点】
- AppConfig を継承・整理
- UIConfig（accent色・chart設定等）は ui/層に移動
- PathConfig をこのファイルに統合

【バージョン履歴】
- ver.1.0.0: 初版
- ver.2.2.2: ストリーミング表示対応（回答の逐次表示 + Agent状態可視化）
"""

from __future__ import annotations
from dataclasses import dataclass, field


@dataclass(frozen=True)
class AppConfig:
    """
    アプリ全体の動作パラメータ。

    Attributes:
        version:              アプリバージョン。ログ・UI表示に使用。
        title:                アプリタイトル。
        gemini_model:         使用するGeminiモデル名。
        companies_csv_path:   企業一覧CSVのパス。
        cache_ttl_seconds:    BQ/GCSスキーマのキャッシュ有効期間（秒）。
        question_history_max: 質問履歴の保持件数上限。
        supplement_timeout:   補足フェーズ（思考ロジック・インフォグラフィック生成）のタイムアウト秒数。
        deep_dive_count:      深掘り質問の生成件数。
        gcs_max_file_bytes:   GCSから取得するファイルのサイズ上限（バイト）。
        prompt_content_limit: プロンプトに含める回答テキストの文字数上限。
        prompt_data_limit:    プロンプトに含めるデータの文字数上限。
        knowledge_preview_len:前提知識のプレビュー表示文字数。
        error_msg_limit:      エラーメッセージの文字数上限。
    """
    version:               str = "ver.5.9.0"
    title:                 str = "意思決定支援AI"
    gemini_model:          str = "gemini-2.5-flash"
    companies_csv_path:    str = "data/companies.csv"
    cache_ttl_seconds:     int = 300
    question_history_max:  int = 5
    supplement_timeout:    int = 60
    deep_dive_count:       int = 3
    gcs_max_file_bytes:    int = 5 * 1024 * 1024  # 5MB
    prompt_content_limit:  int = 1500
    prompt_data_limit:     int = 2000
    knowledge_preview_len: int = 500
    error_msg_limit:       int = 200


@dataclass(frozen=True)
class PathConfig:
    """
    data/{企業フォルダ}/ 以下のディレクトリ名定数。

    これらの名前を変更する場合はここだけ修正すればよい。

    Attributes:
        structured:   構造化データ（.csv, .txt）
        unstructured: 非構造化データ（.txt, .md, .pdf）
        prompts:      回答スタイル定義（.txt, .md, .pdf）
        knowledge:    企業前提知識（.txt, .md, .pdf）
        introduction: はじめに表示するテキスト（.txt, .md）
        templates:    質問テンプレート（.md, .txt）
        smart_cards:  スマートカードプロンプト上書き（{id}.md or {id}.txt）
    """
    structured:   str = "structured"
    unstructured: str = "unstructured"
    prompts:      str = "prompts"
    knowledge:    str = "knowledge"
    introduction: str = "introduction"
    templates:    str = "templates"
    smart_cards:  str = "smart_cards"


class ModelConfig:
    """
    AIモデル設定（ミュータブル — 実行中に切り替え可能）。

    エージェントの役割ごとに最適なモデルを設定する。
    他のファイルからは以下のようにimportして使う：
        from config.app_config import MODELS
        model_name = MODELS.deep
    """
    def __init__(self):
        self.router:     str = "gemini-2.5-flash"    # ルーター（質問分類）
        self.fast:       str = "gemini-2.5-flash"    # 高速回答（スマートカード、V1エンジン）
        self.deep:       str = "gemini-2.5-pro"      # 深い分析（チャット、ADKエンジン）
        self.supplement: str = "gemini-2.5-flash"    # 補足フェーズ（思考ロジック等）

    # 利用可能モデル一覧（Model Garden段階2で動的取得に切り替え予定）
    AVAILABLE_MODELS = [
        {"id": "gemini-2.5-flash", "name": "Gemini 2.5 Flash", "provider": "Google", "speed": "高速", "cost": "低"},
        {"id": "gemini-2.5-pro", "name": "Gemini 2.5 Pro", "provider": "Google", "speed": "標準", "cost": "中"},
        {"id": "claude-opus-4-6", "name": "Claude Opus 4.6（後日ADK対応）", "provider": "Anthropic", "speed": "低速", "cost": "高"},
        {"id": "claude-sonnet-4-6", "name": "Claude Sonnet 4.6（後日ADK対応）", "provider": "Anthropic", "speed": "標準", "cost": "中"},
        {"id": "claude-haiku-4-5", "name": "Claude Haiku 4.5（後日ADK対応）", "provider": "Anthropic", "speed": "高速", "cost": "低"},
    ]

    def to_dict(self) -> dict:
        return {
            "router": self.router,
            "fast": self.fast,
            "deep": self.deep,
            "supplement": self.supplement,
        }


# アプリ全体で使うシングルトンインスタンス
# 他のファイルからは以下のようにimportして使う：
#   from config.app_config import APP, PATHS, MODELS
APP    = AppConfig()
PATHS  = PathConfig()
MODELS = ModelConfig()
