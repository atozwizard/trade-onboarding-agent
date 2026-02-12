"""
ChromaDB Document Retriever Implementation

ChromaDB를 사용한 DocumentRetriever 구현체.
"""
import logging
from typing import List, Dict, Any, Optional
import chromadb
from chromadb.config import Settings as ChromaSettings

from backend.ports.document_retriever import (
    DocumentRetriever,
    RetrievedDocument,
    RetrievalError
)
from backend.config import Settings, get_settings


logger = logging.getLogger(__name__)


class ChromaDocumentRetriever(DocumentRetriever):
    """
    ChromaDB를 사용한 문서 검색

    Features:
        - 메타데이터 필터링 (document_type 등)
        - 유사도 기반 검색
        - 컬렉션 통계

    Example:
        retriever = ChromaDocumentRetriever(get_settings())
        docs = retriever.search("FOB 조건", k=3, document_type="email")
    """

    def __init__(self, settings: Settings):
        """
        Args:
            settings: 애플리케이션 설정 (API 키, ChromaDB 경로 등)
        """
        self._settings = settings

        try:
            # ChromaDB 클라이언트 초기화
            self._client = chromadb.PersistentClient(
                path="backend/rag/chroma_db",
                settings=ChromaSettings(anonymized_telemetry=False)
            )

            # 컬렉션 로드 (없으면 생성)
            self._collection = self._client.get_or_create_collection(
                name="trade_documents"
            )

            doc_count = self._collection.count()
            logger.info(f"ChromaDocumentRetriever initialized: {doc_count} documents")

        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB: {e}")
            raise RetrievalError(f"ChromaDB initialization failed: {e}")

    def search(
        self,
        query: str,
        k: int = 5,
        document_type: Optional[str] = None,
        **filters
    ) -> List[RetrievedDocument]:
        """
        유사도 기반 문서 검색

        Args:
            query: 검색 쿼리
            k: 반환할 문서 개수
            document_type: 문서 타입 필터 (email, common_mistake 등)
            **filters: 추가 메타데이터 필터

        Returns:
            List[RetrievedDocument]: 검색된 문서 (유사도 순)

        Raises:
            RetrievalError: 검색 실패
        """
        try:
            # 메타데이터 필터 구성
            where = {}
            if document_type:
                where["document_type"] = document_type
            where.update(filters)

            # 검색 실행
            logger.debug(f"Searching: query='{query[:50]}...', k={k}, where={where}")

            results = self._collection.query(
                query_texts=[query],
                n_results=k,
                where=where if where else None
            )

            # RetrievedDocument 객체로 변환
            documents = []
            if results["documents"] and results["documents"][0]:
                for i in range(len(results["documents"][0])):
                    doc = RetrievedDocument(
                        content=results["documents"][0][i],
                        metadata=results["metadatas"][0][i] if results.get("metadatas") else {},
                        distance=results["distances"][0][i] if results.get("distances") else 0.0
                    )
                    documents.append(doc)

            logger.info(f"Found {len(documents)} documents")
            return documents

        except Exception as e:
            logger.error(f"Search failed: {e}")
            raise RetrievalError(f"Document search failed: {e}")

    def get_collection_stats(self) -> Dict[str, Any]:
        """
        컬렉션 통계 반환

        Returns:
            Dict: {"total_documents": int, "document_types": List[str]}
        """
        try:
            total_docs = self._collection.count()

            # 모든 메타데이터 가져오기 (샘플링)
            sample = self._collection.get(limit=1000)
            document_types = set()

            if sample.get("metadatas"):
                for metadata in sample["metadatas"]:
                    if "document_type" in metadata:
                        document_types.add(metadata["document_type"])

            return {
                "total_documents": total_docs,
                "document_types": sorted(list(document_types))
            }

        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return {
                "total_documents": 0,
                "document_types": [],
                "error": str(e)
            }

    def __repr__(self) -> str:
        try:
            count = self._collection.count()
            return f"<ChromaDocumentRetriever docs={count}>"
        except:
            return "<ChromaDocumentRetriever (not initialized)>"
