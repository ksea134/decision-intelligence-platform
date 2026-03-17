# BigQuery アップロード手順

## 前提条件
- Google Cloud SDK がインストールされていること
- `decision-support-ai` プロジェクトへのアクセス権限があること
- `demo_factory` データセットが存在すること

## 方法1: Pythonスクリプト（推奨）

### 1. 必要なライブラリをインストール
```bash
pip install google-cloud-bigquery
```

### 2. 認証
```bash
gcloud auth application-default login
gcloud config set project decision-support-ai
```

### 3. スクリプト実行
CSVファイルと同じディレクトリで実行：
```bash
python upload_to_bigquery.py
```

---

## 方法2: bqコマンド（個別実行）

### 認証
```bash
gcloud auth login
gcloud config set project decision-support-ai
```

### 各テーブルをアップロード

```bash
# 1. 製造実行システム
bq load --autodetect --skip_leading_rows=1 --replace \
  demo_factory.mes_a3_line_operation \
  "01_製造実行システム_A-3ライン稼働実績.csv"

# 2. IoTセンサー
bq load --autodetect --skip_leading_rows=1 --replace \
  demo_factory.iot_press_vibration_temp_log \
  "02_IoTセンサー_フ_レス機振動_温度ロク_.csv"

# 3. 設備保全システム
bq load --autodetect --skip_leading_rows=1 --replace \
  demo_factory.equipment_maintenance_history \
  "03_設備保全システム_点検_修理履歴.csv"

# 4. 生産管理システム
bq load --autodetect --skip_leading_rows=1 --replace \
  demo_factory.production_shipment_order_schedule \
  "05_生産管理システム_出荷_受注予定.csv"
```

---

## テーブル一覧

| テーブル名 | 元ファイル | 説明 |
|-----------|-----------|------|
| `mes_a3_line_operation` | 01_製造実行システム... | A-3ライン稼働実績 |
| `iot_press_vibration_temp_log` | 02_IoTセンサー... | プレス機振動・温度ログ |
| `equipment_maintenance_history` | 03_設備保全システム... | 点検・修理履歴 |
| `production_shipment_order_schedule` | 05_生産管理システム... | 出荷・受注予定 |

---

## 確認コマンド

アップロード後、以下で確認：
```bash
# テーブル一覧
bq ls demo_factory

# 各テーブルのスキーマ確認
bq show demo_factory.mes_a3_line_operation

# データプレビュー
bq head demo_factory.mes_a3_line_operation
```

---

## トラブルシューティング

### エンコーディングエラーが出る場合
CSVがUTF-8であることを確認：
```bash
file -i *.csv
```

UTF-8でない場合は変換：
```bash
iconv -f SHIFT-JIS -t UTF-8 input.csv > output.csv
```

### データセットが存在しない場合
```bash
bq mk --dataset decision-support-ai:demo_factory
```
