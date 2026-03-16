"""GCS Service - Streamlit Cloud 対応版"""
from __future__ import annotations
import logging

import streamlit as st
from google.cloud import storage

from infra.gcp_auth import get_credentials
from domain.models import CloudDataResult

logger = logging.getLogger(__name__)


class GCSService:
    def __init__(self, bucket_name: str):
        self.bucket_name = bucket_name
        self._client: storage.Client | None = None

    def _get_client(self) -> storage.Client:
        if self._client is None:
            credentials = get_credentials()
            self._client = storage.Client(credentials=credentials)
        return self._client

    @st.cache_data(ttl=300, show_spinner=False)
    def fetch_documents(_self, bucket_name: str, prefix: str = "", max_size_mb: int = 5) -> CloudDataResult:
        """GCSからドキュメントを取得（キャッシュ付き）"""
        try:
            client = _self._get_client()
            bucket = client.bucket(bucket_name)
            blobs = list(bucket.list_blobs(prefix=prefix))
            
            contents = []
            for blob in blobs:
                if blob.size > max_size_mb * 1024 * 1024:
                    logger.warning(f"Skipping large file: {blob.name} ({blob.size} bytes)")
                    continue
                if blob.name.endswith(('.txt', '.md')):
                    try:
                        text = blob.download_as_text()
                        contents.append(f"--- {blob.name} ---\n{text}")
                    except Exception as e:
                        logger.warning(f"Failed to download {blob.name}: {e}")
            
            combined = "\n\n".join(contents)
            return CloudDataResult(content=combined, is_connected=True)
        
        except Exception as e:
            error_str = str(e).lower()
            if "403" in error_str or "permission" in error_str:
                error_type = "auth"
            elif "404" in error_str or "not found" in error_str:
                error_type = "not_found"
            elif "network" in error_str or "connection" in error_str:
                error_type = "network"
            else:
                error_type = "config"
            
            logger.error(f"GCS fetch failed: {e}")
            return CloudDataResult(
                content="",
                is_connected=False,
                error_type=error_type,
                error_detail=str(e),
            )


# 既存コードとの互換性のための関数インターフェース
_default_service: GCSService | None = None


def _get_service(bucket_name: str) -> GCSService:
    global _default_service
    if _default_service is None or _default_service.bucket_name != bucket_name:
        _default_service = GCSService(bucket_name)
    return _default_service


def fetch_gcs_documents(bucket_name: str, prefix: str = "", max_size_mb: int = 5) -> CloudDataResult:
    """GCSからドキュメントを取得"""
    service = _get_service(bucket_name)
    return service.fetch_documents(bucket_name, prefix, max_size_mb)
