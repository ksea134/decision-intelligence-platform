from __future__ import annotations
import logging
from typing import Any

logger = logging.getLogger(__name__)


class VectorSearchClient:
    """
    Vertex AI Vector Search client.
    Interface only — full implementation is Phase 3.

    This class defines the contract (interface) that the orchestration layer
    depends on. The actual Vertex AI connection will be implemented later
    without changing the interface.
    """

    def __init__(self, project_id: str, index_endpoint: str, deployed_index_id: str) -> None:
        self.project_id = project_id
        self.index_endpoint = index_endpoint
        self.deployed_index_id = deployed_index_id
        self._ready = False
        logger.info("VectorSearchClient initialized (not yet connected)")

    def is_ready(self) -> bool:
        """Return True if the client is connected and ready."""
        return self._ready

    def search(self, query_text: str, top_k: int = 5) -> list[dict[str, Any]]:
        """
        Search for similar documents by query text.

        Args:
            query_text: The query to search for.
            top_k:      Number of results to return.

        Returns:
            List of matching documents with score and content.
            Returns empty list until Phase 3 implementation.
        """
        logger.info("VectorSearchClient.search called (not yet implemented)")
        return []

    def upsert(self, doc_id: str, text: str, metadata: dict[str, Any] | None = None) -> bool:
        """
        Insert or update a document in the vector index.

        Args:
            doc_id:   Unique document identifier.
            text:     Document text to embed and store.
            metadata: Optional metadata dict.

        Returns:
            True on success, False on failure.
            Returns False until Phase 3 implementation.
        """
        logger.info("VectorSearchClient.upsert called (not yet implemented)")
        return False


def create_vector_search_client(
    project_id: str,
    index_endpoint: str = "",
    deployed_index_id: str = "",
) -> VectorSearchClient:
    """
    Factory function to create a VectorSearchClient.
    Centralizes client creation for easy future modification.
    """
    return VectorSearchClient(
        project_id=project_id,
        index_endpoint=index_endpoint,
        deployed_index_id=deployed_index_id,
    )
