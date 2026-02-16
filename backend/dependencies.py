"""
FastAPI Dependency Injection

에이전트 및 서비스 인스턴스를 FastAPI 엔드포인트에 주입.
"""
import logging
from functools import lru_cache
from fastapi import Depends

from backend.config import get_settings
from backend.ports import LLMGateway, DocumentRetriever
from backend.infrastructure import UpstageLLMGateway, ChromaDocumentRetriever
from backend.agents.base import BaseAgent


logger = logging.getLogger(__name__)


@lru_cache()
def get_llm_gateway() -> LLMGateway:
    """
    LLM Gateway 싱글톤 인스턴스 반환

    Returns:
        LLMGateway: Upstage LLM Gateway
    """
    settings = get_settings()
    gateway = UpstageLLMGateway(
        api_key=settings.upstage_api_key,
        model="solar-pro",
        timeout=30
    )
    logger.info("LLM Gateway created")
    return gateway


@lru_cache()
def get_document_retriever() -> DocumentRetriever:
    """
    Document Retriever 싱글톤 인스턴스 반환

    Returns:
        DocumentRetriever: ChromaDB Document Retriever
    """
    settings = get_settings()
    retriever = ChromaDocumentRetriever(settings)
    logger.info("Document Retriever created")
    return retriever


# DEPRECATED: Legacy email agent functions (2026-02-16)
# The modular EmailCoachAgent has been replaced by LangGraph-based email_agent
# These functions are no longer used in routes.py (orchestrator handles routing)
#
# def create_email_agent(
#     llm: LLMGateway = None,
#     retriever: DocumentRetriever = None
# ) -> BaseAgent:
#     """
#     Email Agent 인스턴스 생성 (직접 호출용)
#     """
#     from backend.agents.email import EmailCoachAgent  # Now in docs/YYK/trash/
#     ...
#
# def get_email_agent(
#     llm: LLMGateway = Depends(get_llm_gateway),
#     retriever: DocumentRetriever = Depends(get_document_retriever)
# ) -> BaseAgent:
#     """
#     Email Agent 의존성 주입 (FastAPI Depends 전용)
#     """
#     return create_email_agent(llm, retriever)
