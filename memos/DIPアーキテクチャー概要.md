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
| 4B追加 | Model Garden連携（Claude等） | 段階1完了（モデル切替UI・Claude V1対応） |
| 7A | AI Ops Phase A（ログ・トレース） | 完了 |
| 7B | AI Ops Phase B（メトリクス・アラート） | 完了 |

---

## 6. GCPコンポーネント実装状況（v5.9.1現在）

| コンポーネント | 実装状況 | 停止理由 | 最終的な実装機能 |
|--------------|---------|---------|----------------|
| **Model Garden** | 段階1完了（モデル切替UI、V1+補足でClaude対応、LLM抽象化層） | 段階2（API連携）未実装。段階3はGoogle側の機能未提供 | APIでモデル一覧を動的取得→DIP反映。ADKでもClaude利用可能（Vertex AI経由） |
| **Vertex AI Agent Builder** | 未実装（エージェント定義JSON外部化は完了） | ADKとAgent Builderの統合機能をGoogleが未提供。時期未定 | GCPコンソールからエージェントを閲覧・追加・プロンプト変更・モデル切替 |
| **Vertex AI Evaluation** | 未実装（👍👎フィードバック基盤は完了） | 優先度。フィードバックデータが溜まってから効果を発揮 | 回答品質自動評価（正確性・完全性・ハルシネーション率）。👍👎データと照合して基準校正 |
| **Cloud DLP** | 未実装 | 事業フェーズ3（本番運用）の領域。PoCでは1社のデモデータ | 回答に含まれる機密情報（個人名・口座番号等）を自動マスキング |
| **Dataplex** | 未実装 | 同上。複数企業の本番データを扱い始めてから必要 | 企業別データ分離保証、データアクセス監査証跡、データ品質ルール自動チェック |
| **A2A Protocol** | 未実装 | Google発表の新プロトコル。エコシステムが未成熟。PoCでは外部連携不要 | 外部システムのエージェントと通信・連携（例: ERP在庫照会、Kyndryl Bridge障害情報交換） |
| **MCP** | 未実装 | エコシステム発展途上。現在のツール直接接続が安定動作 | ツール接続の標準化。外部ツール（Slack、Jira、SAP等）を設定だけで追加可能 |
| 6 | Governance層実装 | 未着手 |
| 7 | Observability & FinOps | 未着手 |
| 8 | 高度機能（InlineViz等） | 未着手 |

→ 詳細は `memos/DIP開発ロードマップv2.1.md`
