"""
domain/prompt_builder.py — システムプロンプト組み立て

【役割】
Geminiに渡すシステムプロンプトを、確定した構造通りに組み立てる。

【プロンプト構造（SPEC_v1.md 5-1節より）】
1. ペルソナ宣言     : {company}の意思決定を支援するトップコンサルタント
2. 言語ルール       : ユーザーの言語に合わせる
3. [FILES:]タグ指示 : Grounding機能の根拠。回答末尾に必ず記載させる
4. SQL生成ルール    : BQ接続有無で分岐。未接続時はSQL生成を禁止
5. 企業別前提知識   : knowledge/ の内容
6. 回答フォーマット : prompts/ の内容（最優先指示）
               ※太字ルールもここで定義。コードによる制御は行わない。
7. データ活用指示   : structured / unstructured / BQ / GCS

【設計原則】
- 完全にフレームワーク非依存。
- 純粋な関数として実装。副作用なし。
- 太字（**）の制御はprompts/ファイルに完全に委ねる。
  コードで事後改変しない（旧ensure_minimum_emphasis_for_displayは廃止済み）。

【現行コードからの変更点】
- AIService.build_system_instruction() をドメイン層に分離・独立
- UIへの依存を完全に除去
"""

from __future__ import annotations


def build_system_prompt(
    company: str,
    bq_schema: str,
    gcs_docs: str,
    knowledge: str,
    prompts: str,
    structured: str,
    unstructured: str,
    bq_connected: bool,
) -> str:
    """
    Geminiに渡すシステムプロンプトを組み立てて返す。

    Args:
        company:      対象企業名。例: "株式会社マツダ"
        bq_schema:    BigQueryのスキーマ情報。未接続時は空文字。
        gcs_docs:     GCSから取得したドキュメント。未取得時は空文字。
        knowledge:    knowledge/ ディレクトリの内容。企業前提知識。
        prompts:      prompts/ ディレクトリの内容。回答スタイル定義。
        structured:   structured/ ディレクトリの内容。ローカル構造化データ。
        unstructured: unstructured/ ディレクトリの内容。ローカル非構造化データ。
        bq_connected: BigQueryへの接続が成功しているなら True。

    Returns:
        組み立て済みのシステムプロンプト文字列。
    """
    return (
        _build_persona(company)
        + _build_language_rules()
        + _build_files_tag_instruction()
        + _build_sql_rules(bq_connected)
        + _build_knowledge_section(knowledge)
        + _build_format_section(prompts)
        + _build_data_section(bq_schema, gcs_docs, structured, unstructured, bq_connected)
    )


# ============================================================
# 内部関数 — 各セクションの組み立て
# ============================================================

def _build_persona(company: str) -> str:
    return (
        f"あなたは{company}の意思決定を支援するトップコンサルタントです。\n\n"
    )


def _build_language_rules() -> str:
    return (
        "【言語ルール】\n"
        "- ユーザーの質問が日本語なら日本語で、英語なら英語で回答してください。\n\n"
    )


def _build_files_tag_instruction() -> str:
    return (
        "【システム処理用タグ（必須）】\n"
        "- 回答の最後に必ず [FILES: ファイル名1, ファイル名2] と記載してください。\n"
        "- ファイル名はディレクトリパスを除いたファイル名のみ（拡張子は含む）を記載してください。\n"
        "- ファイル名を [] で囲まないこと。カンマ区切りで列挙してください。\n"
        "- データが存在しない場合は [FILES: なし] と記載してください。\n"
        "- 出典表記・強調ルール・見出し構造は prompts に従ってください。\n\n"
    )


def _build_sql_rules(bq_connected: bool) -> str:
    if not bq_connected:
        return (
            "【SQL生成ルール】\n"
            "- BigQueryへの接続が確立されていないため、SQLを生成してはいけません。\n"
            "- データの分析はローカルファイルまたはGCS資料のみを使用してください。\n"
            "- SQLコードブロック・プレーンテキスト問わず、SQL文を回答本文に一切含めないこと。\n"
            "- BigQueryのテーブル名・データセット名・SQL構文を回答の地の文に露出させないこと。\n\n"
        )
    return (
        "【BigQueryデータ取得ルール — 最重要】\n"
        "\n"
        "■ 必須アクション:\n"
        "以下のキーワードを含む質問には、回答を生成する前に必ず `query_bigquery` ツールを呼び出してください:\n"
        "  売上、収益、利益、コスト、費用、金額、数値、件数、個数、推移、比較、合計、平均、\n"
        "  データ、実績、業績、成績、達成率、前年比、前月比、増減、分析、集計、統計、\n"
        "  「教えて」「見せて」「表示して」「確認して」「調べて」「分析して」\n"
        "\n"
        "■ 絶対禁止パターン:\n"
        "以下のような回答は絶対に生成しないでください:\n"
        "  ❌「データがあれば〜できます」\n"
        "  ❌「このデータを使えば〜算出可能です」\n"
        "  ❌「具体的な数値は手元にございませんが...」\n"
        "  ❌「〜の情報が含まれています」（データを見ずにスキーマだけで回答）\n"
        "\n"
        "■ 正しい行動:\n"
        "  ✅ まず `query_bigquery` でデータを取得\n"
        "  ✅ 取得した実際の数値を回答に含める\n"
        "  ✅ 「2025年の総売上は134,567,000円です」のように具体的な数値で回答\n"
        "\n"
        "■ SQL実行ルール:\n"
        "- スキーマに記載されていないテーブルへのSQLは絶対に生成しないでください。\n"
        "- SELECT文のみ使用可能です。INSERT/UPDATE/DELETE等は禁止。\n"
        "- 日本語のカラム名・テーブル名は必ずバッククォート(`)で囲んでください。\n"
        "  例: SELECT `稼働率_pct`, `計測日時` FROM `demo_factory`.`mes_a3_line_operation`\n"
        "- ツールから得られた数値を、回答本文に必ず記載してください。\n"
        "- SQL文そのものを回答本文に絶対に記載しないでください。\n\n"
    )


def _build_knowledge_section(knowledge: str) -> str:
    return (
        "【企業別前提知識】\n"
        f"{knowledge or '特になし。'}\n\n"
    )


def _build_format_section(prompts: str) -> str:
    return (
        "【回答フォーマット・役割（最優先指示）】\n"
        "以下の指示はすべての回答に必ず従うこと。"
        "見出し・強調・体裁・役割・思考スタイル・太字ルールのすべてはここで定義する。\n\n"
        f"{prompts or '客観的かつ簡潔に分析してください。'}\n\n"
    )


def _build_data_section(
    bq_schema: str,
    gcs_docs: str,
    structured: str,
    unstructured: str,
    bq_connected: bool,
) -> str:
    has_local = bool(structured.strip() or unstructured.strip())
    section = ""

    if has_local:
        section += "【一次データ（ローカルファイル）— 最優先で参照すること】\n"
        if structured.strip():
            section += f"■ 構造化データ:\n{structured}\n\n"
        if unstructured.strip():
            section += f"■ 非構造化データ:\n{unstructured}\n\n"

    if bq_connected and bq_schema.strip():
        section += (
            "【クラウドデータ（BigQuery / GCS）】\n"
            "■ BigQueryスキーマ（データ取得に必ず使用すること）:\n"
            "  ※数値・実績に関する質問を受けたら、以下のスキーマを参照して\n"
            "    query_bigquery ツールでSQLを実行し、実データを取得してから回答すること。\n"
            "  ※スキーマ情報だけを見て「〜のデータがあります」と回答するのは禁止。\n"
            f"{bq_schema}\n\n"
        )

    if gcs_docs.strip():
        section += f"■ GCS資料:\n{gcs_docs}\n"

    if section:
        section = "【データ活用】\n- すべてのデータを踏まえて回答を生成してください。\n\n" + section

    return section
