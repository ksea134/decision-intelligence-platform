# DIPアーキテクチャー概要

> 作成日: 2026-03-18
> 更新日: 2026-03-19

このファイルはDIPの全体像を示す。各層の詳細は個別の仕様書を参照。

---

## 1. DIPとは

Decision Intelligence Platform（DIP）は、企業のデータを活用した意思決定支援AIチャットアプリケーション。ユーザーが自然言語で質問すると、BigQuery上の構造化データやGCS上のドキュメントをもとに、分析・比較・予測などの回答を生成する。

---

## 2. 7層構造

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        統合運用: Kyndryl Bridge                         │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
┌───────────────────────┬───────────┴───────────┬───────────────────────┐
│ Security & Governance │      AI Core System    │  AI Ops & Observability│
│      守りの要         │                        │    進化と品質の監視    │
├───────────────────────┼────────────────────────┼───────────────────────┤
│ ・VPC Service Controls│  UI/UX層               │ ・Kyndryl Bridge      │
│ ・Cloud Identity/IAM  │   └ Cloud Run + IAP    │   Connector           │
│ ・Cloud DLP           │   └ Grounding機能      │ ・Cloud Monitoring    │
│ ・Cloud KMS(CMKS)     │                        │   / Logging           │
│                       │  Orchestration層       │ ・Vertex AI Evaluation│
│                       │   └ Vertex AI Agent    │ ・Human in the loop   │
│                       │     Builder            │ ・FinOps/Cost Mgmt    │
│                       │   └ Reasoning Engine   │                       │
│                       │   └ Memory Store       │                       │
│                       │   └ Vertex AI Search   │                       │
│                       │                        │                       │
│                       │  Model層               │                       │
│                       │   └ Gemini 2.5 Pro     │                       │
│                       │   └ Gemini 2.5 Flash   │                       │
│                       │   └ Model Garden       │                       │
│                       │                        │                       │
│                       │  Governance層          │                       │
│                       │   └ Dataplex           │                       │
│                       │                        │                       │
│                       │  Storage層             │                       │
│                       │   └ BigQuery Storage   │                       │
│                       │   └ BigLake            │                       │
│                       │   └ Cloud Storage      │                       │
│                       │                        │                       │
│                       │  Ingestion層           │                       │
│                       │   └ Data Fusion        │                       │
│                       │   └ Dataflow           │                       │
└───────────────────────┴────────────────────────┴───────────────────────┘
                                    │
┌─────────────────────────────────────────────────────────────────────────┐
│ DataSource: SAP, Salesforce, ServiceNow, DB, Excel, PPT, Word, PDF...  │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 3. 層別仕様書一覧

| 層 | ファイル | 概要 | 状態 |
|---|---|---|---|
| **UI/UX層** | `memos/層別仕様_UI-UX層.md` | Streamlit、チャットUI、スマートカード、将来のCloud Run + IAP | 実装済み（MVP） |
| **Orchestration層** | `memos/層別仕様_Orchestration層.md` | Reasoning Engine、エージェント構成、Vertex AI Search、キャッシュ、処理フロー | 実装済み（v4 + ADK） |
| **Model層** | `memos/層別仕様_Model層.md` | Gemini Flash/Pro使い分け、将来のModel Garden連携、Gemini vs Claude比較 | 一部実装済み |
| **Governance層** | `memos/層別仕様_Governance層.md` | Dataplex、行/列レベルアクセス制御、DLP、データリネージュ | 未着手（Phase 6） |
| **Storage層** | `memos/層別仕様_Storage層.md` | BigQuery、GCS、ローカルファイル、Vertex AI Searchストア | 実装済み |
| **Ingestion層** | `memos/層別仕様_Ingestion層.md` | Data Fusion、Dataflow、現在は手動アップロード | 未着手（手動運用中） |
| **DataSource層** | `memos/層別仕様_DataSource層.md` | SAP、Salesforce、ServiceNow等の外部システム、A2A連携 | 将来Phase |

### 横断ドキュメント

| ドキュメント | 概要 |
|---|---|
| `memos/層別仕様_Security＆Governance層.md` | Security & Governance柱: 対策一覧、3段階アクセス制御、IAP、開発時の機密データ保護 |
| `memos/層別仕様_AI Ops＆Observability層.md` | AI Ops & Observability柱: 監視、品質評価、FinOps、Human in the Loop |
| `memos/開発ルール.md` | 全ルール・テスト項目・開発プロセス |

---

## 4. 現在のバージョンと状態

| 項目 | 内容 |
|---|---|
| 現行バージョン | v4（v2.4.0-stable以降） |
| メインモデル | Gemini 2.5 Flash / Pro（エージェント種別で自動選択） |
| GCPプロジェクト | decision-support-ai |
| リポジトリ | https://github.com/ksea134/decision-intelligence-platform |
| Cloud Run（本番） | https://dip-897403315215.asia-northeast1.run.app（IAP認証付き） |
| Streamlit Cloud（旧） | https://dip134.streamlit.app/ |

---

## 5. ロードマップ進捗

| Phase | 名称 | ステータス |
|-------|------|-----------|
| 0 | 基盤準備・仕様策定 | 完了 |
| 1 | Agent Router | 完了（V1統合済み） |
| 2 | Memory Store統合 | スキップ（当面インメモリで運用） |
| 3 | Vertex AI Search統合 | 完了 |
| 4A | Agent Builder基盤 | 完了（ADK統合済み） |
| 4B | エコシステム連携 | 一部完了（Gemini Flash/Pro使い分け） |
| 5 | エンタープライズUI移行 | 一部完了（Cloud Run + IAP設定済み） |
| 4B追加 | Model Garden連携（Claude等） | 未着手（Phase 5の後に実施） |
| 6 | Governance層実装 | 未着手 |
| 7 | Observability & FinOps | 未着手 |
| 8 | 高度機能（InlineViz等） | 未着手 |

→ 詳細は `memos/DIP開発ロードマップv2.1.md`
