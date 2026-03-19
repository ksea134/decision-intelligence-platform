# DIP Storage層 仕様

> 作成日: 2026-03-19
> ステータス: BigQuery / GCS / ローカルファイル — 実装済み

---

## 1. 役割

DIPが利用する全データの格納・管理を担う。構造化データ（BigQuery）、非構造化データ（GCS）、ローカルファイルの3系統。

## 2. データソース構成

```
┌──────────────────────────────────────────────────────────────┐
│  Storage層                                                    │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────┐  │
│  │ BigQuery     │  │ GCS          │  │ ローカルファイル     │  │
│  │ 構造化データ  │  │ ドキュメント  │  │ data/{企業名}/      │  │
│  │ 売上、KPI等  │  │ 報告書、分析  │  │ prompts, knowledge │  │
│  └──────────────┘  └──────────────┘  └────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
```

## 3. BigQuery

| 項目 | 内容 |
|------|------|
| GCPプロジェクト | decision-support-ai |
| リージョン | asia-northeast1（東京）/ US |
| データセット命名規則 | companies.csvのフォルダ名と一致 |
| データ取得方式 | `SELECT * FROM table LIMIT 100`（v4で固定化） |
| 接続ファイル | `infra/bigquery_service.py` |
| キャッシュ | スキーマ: `@st.cache_data`（TTL 5分） |

### クラウド優先ロジック

- BQ接続成功 → ローカルの構造化データ（structured/）を抑制
- GCS接続成功 → ローカルの非構造化データ（unstructured/）を抑制
- 両方失敗 → ローカルデータをそのまま使用
- 全データなし → チャット無効化

実装: `orchestration/agents/data_agent.py` の `_apply_cloud_priority()`

## 4. GCS（Google Cloud Storage）

| 項目 | 内容 |
|------|------|
| バケット | dsa-knowledge-base |
| プレフィックス | `{フォルダ名}/unstructured/` |
| 対応拡張子 | .txt, .md |
| サイズ制限 | 5MB以内 |
| 接続ファイル | `infra/gcs_service.py` |
| キャッシュ | `@st.cache_data`（TTL 5分） |

### 現在GCSにデータがある企業

| フォルダ | ファイル数 |
|---------|----------|
| mazda/ | 23 |
| 7andi_audit/ | 13 |
| demo_factory/ | 10 |
| test01/ | 2 |
| test02/ | 3 |
| test03/ | 5 |

## 5. ローカルファイル

企業ごとに以下のディレクトリ構造を持つ。

```
data/{企業名}/
├── introduction/        ← 「はじめに」に表示されるテキスト
│   └── readme.md
├── knowledge/           ← 企業の前提知識（業界情報、用語集等）
│   └── *.md / *.txt
├── prompts/             ← AIの回答スタイル・役割の定義
│   └── prompt.md        ← 必須
├── smart_cards/         ← チャット画面のショートカットプロンプト
│   ├── alert.md / hint.md / kpi.md / notable.md / recent.md
├── structured/          ← CSVなどの構造化データ
│   └── *.csv
├── templates/           ← 質問テンプレート
│   └── questions.txt
└── unstructured/        ← テキスト・報告書などの非構造化データ
    └── *.txt / *.md
```

読込ファイル: `infra/file_loader.py`

## 6. Vertex AI Search（長期記憶ストア）

Q&Aの永続保存先。Orchestration層の一部だが、ストレージとしての側面もある。

| 項目 | 内容 |
|------|------|
| データストアID | dip-knowledge-store |
| 検索アプリID | dip-search-app |
| 保存内容 | 質問、回答（先頭2000文字）、企業名、エージェント分類、日時 |
| 保存期間 | 無期限 |
| 接続ファイル | `infra/vertex_ai_search.py` |

## 7. 将来の拡張

| 拡張 | Phase | 説明 |
|------|-------|------|
| BigLake | Phase 6 | BigQueryとGCSの統合アクセス |
| Redis Memorystore | Phase 5 | セッション記憶の永続化 |
| Cloud SQL | 将来検討 | リレーショナルデータの管理 |
