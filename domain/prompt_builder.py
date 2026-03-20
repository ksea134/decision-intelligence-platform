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
    intent: str | None = None,
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
        + _build_intent_section(intent)
        + _build_viz_tag_instruction()
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


def _build_intent_section(intent: str | None) -> str:
    if not intent or intent == "general":
        return ""

    if intent == "analysis":
        return (
            "【分析フレームワーク — 要因分析モード】\n"
            "この質問は「原因・要因の特定」を求めています。以下のフレームワークを適用してください。\n\n"
            "■ 5 Whys（5つのなぜ）:\n"
            "  問題の根本原因に到達するまで「なぜ？」を最低3回繰り返す。\n\n"
            "■ 寄与度分析:\n"
            "  各要因の影響度を%で推定。合計100%になるように配分。\n\n"
            "■ 回答構成:\n"
            "  1. 問題の定義（質問を明確な問題文に再定義）\n"
            "  2. 主要因の特定（寄与度%付き）\n"
            "  3. 根本原因分析（5 Whys）\n"
            "  4. 推奨アクション（短期/中期/長期）\n\n"
        )

    if intent == "comparison":
        return (
            "【分析フレームワーク — 比較分析モード】\n"
            "この質問は「複数対象の比較」を求めています。以下のフレームワークを適用してください。\n\n"
            "■ 比較軸の設定:\n"
            "  定量指標（売上、コスト、成長率等）と定性指標（品質、満足度等）の両面から比較。\n\n"
            "■ 比較表の作成:\n"
            "  3〜5つの主要軸で比較表を作成。差分（+/-）を明記。\n\n"
            "■ 回答構成:\n"
            "  1. 比較対象の定義（表形式）\n"
            "  2. 比較表（数値・差分・優位を含む）\n"
            "  3. 各対象の強み・弱み\n"
            "  4. 総合評価と推奨事項\n\n"
        )

    if intent == "forecast":
        return (
            "【分析フレームワーク — 予測分析モード】\n"
            "この質問は「将来の見通し・予測」を求めています。以下のフレームワークを適用してください。\n\n"
            "■ 3シナリオ分析:\n"
            "  楽観（15-25%）/ 基本（50-70%）/ 悲観（15-25%）の3パターンで予測。\n\n"
            "■ 予測の根拠:\n"
            "  過去データのトレンド、季節性、外部環境要因を考慮。\n\n"
            "■ 回答構成:\n"
            "  1. 予測の前提条件（期間、対象指標、基準値）\n"
            "  2. シナリオ別予測（表形式: 予測値/成長率/確率）\n"
            "  3. リスク要因と影響度\n"
            "  4. 推奨アクション\n\n"
        )

    return ""


def _build_language_rules() -> str:
    return (
        "【言語ルール】\n"
        "- ユーザーの質問が日本語なら日本語で、英語なら英語で回答してください。\n"
        "- 回答にコードブロック（```tool_code、```python等）を含めないでください。自然言語のみで回答すること。\n\n"
    )


def _build_viz_tag_instruction() -> str:
    return (
        "【チャート描画タグ（任意）】\n"
        "回答の中で、数値データをチャートで可視化すると理解が深まる箇所には、\n"
        "以下の形式で <viz> タグを挿入してください。\n\n"
        "■ 形式:\n"
        '<viz type="bar" title="チャートのタイトル">\n'
        '{"labels": ["ラベル1","ラベル2","ラベル3"], "data": [100,200,150]}\n'
        "</viz>\n\n"
        "■ 使えるチャートタイプ:\n"
        '- type="bar" : 棒グラフ（比較に最適）\n'
        '- type="line" : 折れ線グラフ（推移・トレンドに最適）\n'
        '- type="pie" : 円グラフ（構成比に最適）\n\n'
        "■ ルール:\n"
        "- チャートは回答の流れの中に自然に配置すること（末尾にまとめない）\n"
        "- labelsとdataの要素数は必ず一致させること\n"
        "- dataの値は数値のみ（文字列は不可）\n"
        "- 1回答あたりチャートは最大3つまで\n"
        "- チャートが不要な回答では <viz> タグを使わないこと\n\n"
    )


def _build_files_tag_instruction() -> str:
    return (
        "【出典情報の記載ルール（必須）】\n"
        "回答の末尾に必ず [FILES: ...] タグを記載してください。\n\n"
        "■ 記載すべき内容:\n"
        "回答生成に使用したすべてのデータソースを記載:\n"
        "- BigQueryテーブル: BQ:テーブル名 （例: BQ:production_results, BQ:equipment_alerts）\n"
        "- GCSドキュメント: GCS:ファイル名 （例: GCS:inspection_report_2026-03-18.txt）\n"
        "- ローカルファイル: LOCAL:ファイル名 （例: LOCAL:factory_overview.txt）\n\n"
        "■ 記載例:\n"
        "[FILES: BQ:production_results, BQ:equipment_alerts, GCS:inspection_report_2026-03-18.txt]\n\n"
        "■ 禁止事項:\n"
        "- 「なし」は禁止。回答を生成した以上、必ず何かのデータを参照しています。\n"
        "- 最低1つ以上のデータソースを記載すること。\n"
        "- 曖昧な記載（「データベース」「ドキュメント」等）は禁止。具体的なテーブル名・ファイル名を記載。\n\n"
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
        section += (
            "■ GCS資料（報告書・分析レポート — 必ず回答に反映すること）:\n"
            "  ※以下の資料には数値の背景・原因・考察が含まれている。\n"
            "  ※数値データ（BigQuery）と合わせて、資料の内容も必ず踏まえて回答すること。\n"
            "  ※数値だけの回答は不十分。資料に書かれた背景・要因・提言も含めること。\n"
            f"{gcs_docs}\n"
        )

    if section:
        section = "【データ活用】\n- すべてのデータ（数値＋報告書）を踏まえて回答を生成してください。\n\n" + section

    return section
