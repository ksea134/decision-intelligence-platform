"""
infra/vertex_ai_search.py — Vertex AI Search クライアント

【役割】
Vertex AI Search（Discovery Engine）を使用して、過去のQ&Aの保存・検索を行う。
DIPの長期記憶として機能し、使えば使うほど賢くなるAIを実現する。

【設計原則】
- フレームワーク非依存。UIに依存しない。
- 失敗時は空の結果を返す（DIPの動作を止めない）。
- チャット本体（reasoning_engine.py）への影響を最小化。
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from typing import Any

logger = logging.getLogger(__name__)

# Discovery Engine SDK
try:
    from google.cloud import discoveryengine_v1 as discoveryengine
    from google.api_core.exceptions import GoogleAPICallError
    DISCOVERY_ENGINE_AVAILABLE = True
except ImportError:
    discoveryengine = None
    GoogleAPICallError = Exception
    DISCOVERY_ENGINE_AVAILABLE = False
    logger.warning("google-cloud-discoveryengine not installed")


class VertexAISearchClient:
    """
    Vertex AI Search クライアント。

    - store(): Q&Aをデータストアに保存
    - search(): 類似した過去のQ&Aを検索
    - is_ready(): 接続可能かどうか
    """

    def __init__(
        self,
        project_id: str,
        data_store_id: str = "dip-knowledge-store",
        location: str = "global",
    ) -> None:
        self._project_id = project_id
        self._data_store_id = data_store_id
        self._location = location
        self._ready = False

        if not DISCOVERY_ENGINE_AVAILABLE:
            logger.warning("[VertexAISearch] SDK not available")
            return

        try:
            # クライアント初期化
            self._doc_client = discoveryengine.DocumentServiceClient()
            self._search_client = discoveryengine.SearchServiceClient()
            self._ready = True
            logger.info("[VertexAISearch] Initialized: project=%s, data_store=%s", project_id, data_store_id)
        except Exception as e:
            logger.error("[VertexAISearch] Init failed: %s", e)

    def is_ready(self) -> bool:
        return self._ready

    @property
    def _parent(self) -> str:
        return (
            f"projects/{self._project_id}"
            f"/locations/{self._location}"
            f"/collections/default_collection"
            f"/dataStores/{self._data_store_id}"
        )

    @property
    def _serving_config(self) -> str:
        return f"{self._parent}/servingConfigs/default_search"

    def store(
        self,
        question: str,
        answer: str,
        company: str,
        intent: str = "general",
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        """
        Q&Aをデータストアに保存する。

        Args:
            question: ユーザーの質問
            answer: AIの回答
            company: 企業名
            intent: エージェント分類（analysis/comparison/forecast/general）
            metadata: 追加メタデータ

        Returns:
            保存成功ならTrue
        """
        if not self._ready:
            return False

        doc_id = f"qa-{int(time.time())}-{uuid.uuid4().hex[:8]}"

        # ドキュメントの内容をJSON構造化テキストとして保存
        content = (
            f"質問: {question}\n\n"
            f"回答: {answer}\n\n"
            f"企業: {company}\n"
            f"分類: {intent}\n"
            f"日時: {time.strftime('%Y-%m-%d %H:%M:%S')}"
        )

        try:
            document = discoveryengine.Document(
                id=doc_id,
                json_data=json.dumps({
                    "question": question,
                    "answer": answer[:2000],  # 回答は先頭2000文字に制限
                    "company": company,
                    "intent": intent,
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                }, ensure_ascii=False),
                content=discoveryengine.Document.Content(
                    raw_bytes=content.encode("utf-8"),
                    mime_type="text/plain",
                ),
            )

            request = discoveryengine.CreateDocumentRequest(
                parent=f"{self._parent}/branches/default_branch",
                document=document,
                document_id=doc_id,
            )

            self._doc_client.create_document(request=request)
            logger.info("[VertexAISearch] Stored Q&A: id=%s, company=%s", doc_id, company)
            return True

        except Exception as e:
            logger.error("[VertexAISearch] Store failed: %s", e)
            return False

    def search(
        self,
        query: str,
        company: str = "",
        top_k: int = 3,
    ) -> list[dict[str, Any]]:
        """
        類似した過去のQ&Aを検索する。

        Args:
            query: 検索クエリ（ユーザーの質問）
            company: 企業名でフィルタ（空文字なら全企業）
            top_k: 返す件数

        Returns:
            類似Q&Aのリスト。各要素は {"question", "answer", "company", "score"} を含む。
            失敗時は空リスト。
        """
        if not self._ready:
            return []

        try:
            # フィルタ条件
            filter_str = f'company: ANY("{company}")' if company else ""

            request = discoveryengine.SearchRequest(
                serving_config=self._serving_config,
                query=query,
                page_size=top_k,
                filter=filter_str if filter_str else None,
            )

            response = self._search_client.search(request=request)

            results = []
            for result in response.results:
                doc = result.document
                # struct_data から取得（Discovery Engineが自動変換）
                data = dict(doc.struct_data) if doc.struct_data else {}
                # struct_data が空の場合は json_data を試行
                if not data and doc.json_data:
                    try:
                        data = json.loads(doc.json_data)
                    except (json.JSONDecodeError, TypeError):
                        data = {}

                results.append({
                    "question": str(data.get("question", "")),
                    "answer": str(data.get("answer", "")),
                    "company": str(data.get("company", "")),
                    "intent": str(data.get("intent", "")),
                    "timestamp": str(data.get("timestamp", "")),
                    "doc_id": doc.id,
                })

            logger.info("[VertexAISearch] Search: query='%s', results=%d", query[:50], len(results))
            return results

        except Exception as e:
            logger.error("[VertexAISearch] Search failed: %s", e)
            return []


def create_search_client(
    project_id: str,
    data_store_id: str = "dip-knowledge-store",
) -> VertexAISearchClient:
    """ファクトリ関数"""
    return VertexAISearchClient(project_id=project_id, data_store_id=data_store_id)
