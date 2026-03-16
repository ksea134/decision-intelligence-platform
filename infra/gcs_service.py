from __future__ import annotations
import logging
from domain.models import CloudDataResult
from config.app_config import APP
from infra.bigquery_service import classify_cloud_error

logger = logging.getLogger(__name__)


def fetch_gcs_documents(bucket: str, gcs_prefix: str) -> CloudDataResult:
    """
    Fetch text documents from GCS bucket.
    Only .txt and .md files are fetched.
    Files exceeding 5MB are skipped with a note.
    No UI dependencies. Cache strategy is handled by the caller.
    """
    try:
        from google.cloud import storage
        client = storage.Client()
        blobs = client.bucket(bucket).list_blobs(prefix=gcs_prefix)

        parts: list[str] = []
        skipped: list[str] = []

        for blob in blobs:
            if not blob.name.lower().endswith((".txt", ".md")):
                continue
            if blob.size and blob.size > APP.gcs_max_file_bytes:
                skipped.append(blob.name + " (" + str(blob.size // 1024) + "KB - size limit exceeded)")
                continue
            rel = blob.name[len(gcs_prefix):]
            text = blob.download_as_text()
            parts.append("[GCS: " + rel + "]\n" + text)

        content = "\n\n".join(parts) if parts else "(no GCS documents)"
        if skipped:
            content += "\n\n[Skipped files]\n" + "\n".join(skipped)

        return CloudDataResult(content=content, is_connected=True)

    except Exception as exc:
        etype, edetail = classify_cloud_error(exc)
        logger.error("GCS fetch failed [%s]: %s", etype, edetail)
        return CloudDataResult(content="", is_connected=False, error_type=etype, error_detail=edetail)
