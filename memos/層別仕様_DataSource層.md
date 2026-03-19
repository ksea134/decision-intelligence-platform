# DIP DataSource層 仕様

> 作成日: 2026-03-19
> ステータス: BigQuery / GCS / ローカルファイルで接続済み。外部システム連携は将来Phase

---

## 1. 役割

DIPが分析対象とするデータの元となる外部システム・ファイル。Ingestion層を通じてStorage層に取り込まれる。

## 2. 現在接続済みのデータソース

| データソース | 接続方式 | 取り込み先 | 状態 |
|-------------|---------|-----------|------|
| CSV/Excel | 手動アップロード | BigQuery | ✅ 運用中 |
| テキスト/Markdown | 手動アップロード | GCS / ローカル | ✅ 運用中 |

## 3. 将来の接続対象

| データソース | 種類 | 接続方式 | Phase |
|-------------|------|---------|-------|
| **SAP** | ERP（財務、購買、在庫） | Data Fusion SAPコネクタ or SAP BTP連携 | 将来 |
| **Salesforce** | CRM（顧客、商談、売上） | Data Fusion Salesforceコネクタ | 将来 |
| **ServiceNow** | ITSM（インシデント、変更管理） | REST API経由 | 将来 |
| **RDB（Oracle, SQL Server等）** | 基幹DB | JDBC接続 via Data Fusion | 将来 |
| **Excel / CSV** | スプレッドシート | 手動 or Cloud Functions自動取込 | ✅ 運用中 |
| **PDF / Word / PPT** | 報告書・プレゼン資料 | Document AI → GCS | 将来 |
| **社内Wiki / SharePoint** | ナレッジベース | API経由 | 将来 |
| **IoTセンサー** | 工場・設備データ | Pub/Sub → Dataflow → BigQuery | 将来 |

## 4. 外部エージェント連携（A2Aプロトコル）

Phase 4Bで検討中。DIPが外部のAIエージェントとデータ・分析結果を相互にやり取りする。

| 外部エージェント | 提供元 | データ |
|----------------|--------|--------|
| Agentforce | Salesforce | 顧客インサイト、商談予測 |
| Joule | SAP | 財務分析、購買最適化 |
| Now Assist | ServiceNow | インシデント分析、運用最適化 |

```
DIP ←→ A2Aプロトコル ←→ 外部エージェント
      JSON-RPC通信
      Agent Card交換
```

## 5. データソース追加手順

新しいデータソースを追加する際の基本フロー:

```
1. データソースの種類を特定（構造化/非構造化）
2. 取り込み先を決定（BigQuery / GCS / ローカル）
3. 取り込み方法を決定（手動 / Data Fusion / Dataflow等）
4. companies.csvに企業を登録
5. BigQueryにデータセット・テーブルを作成
6. GCSにドキュメントをアップロード
7. DIPで動作確認
```

→ 具体的な手順は `memos/作業マニュアル.md` セクション5
