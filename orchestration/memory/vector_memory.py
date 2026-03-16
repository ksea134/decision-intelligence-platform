from __future__ import annotations
import logging
from typing import Any
from infra.vector_search_client import VectorSearchClient, create_vector_search_client

logger = logging.getLogger(__name__)


class VectorMemory:
    """
    Long-term memory using Vertex AI Vector Search.
    Interface only — full implementation is Phase 3.

    Wraps VectorSearchClient to provide a memory-oriented API:
    - remember(): store a document or analysis result
    - recall():   retrieve relevant past documents by query
    """

    def __init__(self, client: VectorSearchClient) -> None:
        self._client = client

    def is_ready(self) -> bool:
        return self._client.is_ready()

    def recall(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        """
        Retrieve relevant past documents by semantic similarity.
        Returns empty list until Phase 3 implementation.
        """
        if not self._client.is_ready():
            return []
        return self._client.search(query, top_k=top_k)

    def remember(self, doc_id: str, text: str, metadata: dict[str, Any] | None = None) -> bool:
        """
        Store a document in long-term memory.
        Returns False until Phase 3 implementation.
        """
        if not self._client.is_ready():
            return False
        return self._client.upsert(doc_id, text, metadata)


def create_vector_memory(project_id: str) -> VectorMemory:
    """Factory function. Index endpoint config will be added in Phase 3."""
    client = create_vector_search_client(project_id)
    return VectorMemory(client)
