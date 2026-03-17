#!/usr/bin/env python3
"""
BigQuery CSVアップロードスクリプト
Project: decision-support-ai
Dataset: demo_factory
"""

from google.cloud import bigquery
from pathlib import Path

# 設定
PROJECT_ID = "decision-support-ai"
DATASET_ID = "demo_factory"

# アップロード対象ファイルとテーブル名のマッピング
FILE_TABLE_MAPPING = [
    {
        "file": "01_製造実行システム_A-3ライン稼働実績.csv",
        "table": "mes_a3_line_operation",
        "description": "A-3ライン稼働実績（製造実行システム）"
    },
    {
        "file": "02_IoTセンサー_フ_レス機振動_温度ロク_.csv",
        "table": "iot_press_vibration_temp_log",
        "description": "プレス機振動・温度ログ（IoTセンサー）"
    },
    {
        "file": "03_設備保全システム_点検_修理履歴.csv",
        "table": "equipment_maintenance_history",
        "description": "点検・修理履歴（設備保全システム）"
    },
    {
        "file": "05_生産管理システム_出荷_受注予定.csv",
        "table": "production_shipment_order_schedule",
        "description": "出荷・受注予定（生産管理システム）"
    },
]


def upload_csv_to_bigquery(client: bigquery.Client, csv_path: Path, table_id: str, description: str):
    """CSVファイルをBigQueryにアップロード"""
    
    full_table_id = f"{PROJECT_ID}.{DATASET_ID}.{table_id}"
    
    job_config = bigquery.LoadJobConfig(
        source_format=bigquery.SourceFormat.CSV,
        skip_leading_rows=1,  # ヘッダー行をスキップ
        autodetect=True,      # スキーマ自動検出（カラム名を1行目から取得）
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,  # 既存テーブルは上書き
    )
    
    print(f"📤 アップロード中: {csv_path.name} → {table_id}")
    
    with open(csv_path, "rb") as f:
        load_job = client.load_table_from_file(f, full_table_id, job_config=job_config)
    
    # ジョブ完了を待機
    load_job.result()
    
    # 結果確認
    table = client.get_table(full_table_id)
    print(f"   ✅ 完了: {table.num_rows}行 をロード")
    
    # テーブルの説明を更新
    table.description = description
    client.update_table(table, ["description"])
    
    return table


def main():
    # BigQueryクライアント初期化
    client = bigquery.Client(project=PROJECT_ID)
    
    print(f"🚀 BigQueryアップロード開始")
    print(f"   Project: {PROJECT_ID}")
    print(f"   Dataset: {DATASET_ID}")
    print("-" * 50)
    
    # CSVファイルのディレクトリ（このスクリプトと同じ場所を想定）
    csv_dir = Path(".")
    
    success_count = 0
    for mapping in FILE_TABLE_MAPPING:
        csv_path = csv_dir / mapping["file"]
        
        if not csv_path.exists():
            print(f"⚠️  ファイルが見つかりません: {mapping['file']}")
            continue
        
        try:
            upload_csv_to_bigquery(
                client, 
                csv_path, 
                mapping["table"],
                mapping["description"]
            )
            success_count += 1
        except Exception as e:
            print(f"   ❌ エラー: {e}")
    
    print("-" * 50)
    print(f"🎉 完了: {success_count}/{len(FILE_TABLE_MAPPING)} テーブルをアップロード")


if __name__ == "__main__":
    main()
