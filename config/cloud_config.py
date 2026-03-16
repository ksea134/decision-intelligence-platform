"""
config/cloud_config.py — クラウド接続先の設定

【役割】
GCP Project ID・GCS Bucket名・企業フォルダ名を保持する。
これらの値からBigQueryのデータセットIDやGCSのプレフィックスを導出する。

【設計原則】
- frozen=True（不変）なデータクラス。値を保持するだけで処理は行わない。
- 計算済みプロパティ（@property）で関連する値を導出する。
- フレームワーク非依存。

【現行コードからの継承】
- CloudConfig をそのまま継承
"""

from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class CloudConfig:
    """
    クラウド接続先の設定値。

    UIのサイドバーで入力された値を保持し、
    BigQuery・GCSへの接続時に必要な値を提供する。

    Attributes:
        project_id:  GCP Project ID。例: "decision-support-ai"
        gcs_bucket:  GCS Bucket名。例: "dsa-knowledge-base"
        folder_name: 選択中の企業フォルダ名。companies.csv の2列目の値。
    """
    project_id:  str
    gcs_bucket:  str
    folder_name: str

    @property
    def dataset_id(self) -> str:
        """BigQueryのデータセットID。企業フォルダ名と同じ。"""
        return self.folder_name

    @property
    def full_dataset_id(self) -> str:
        """BigQueryの完全修飾データセットID。例: "my-project.my_company" """
        return f"{self.project_id}.{self.dataset_id}"

    @property
    def gcs_prefix(self) -> str:
        """GCSのドキュメント取得プレフィックス。例: "my_company/unstructured/" """
        return f"{self.folder_name}/unstructured/"

    @property
    def is_configured(self) -> bool:
        """Project IDとBucket名が両方入力済みかどうか。"""
        return bool(self.project_id.strip() and self.gcs_bucket.strip())
