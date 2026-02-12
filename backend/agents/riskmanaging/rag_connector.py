# backend/agents/riskmanaging/rag_connector.py

from typing import List, Dict, Any, Optional
import os
import sys

# Ensure backend directory is in path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '..', '..', '..')) # Go up three levels to reach backend
sys.path.append(project_root)

from backend.config import get_settings
from backend.rag.retriever import search as rag_search
from backend.agents.riskmanaging.config import RAG_DATASETS

class RAGConnector:
    def __init__(self):
        self.settings = get_settings()
        if not self.settings.upstage_api_key:
            print("Warning: UPSTAGE_API_KEY is not set. RAG searches may not function.")

    def get_risk_documents(self, query: str, conversation_history: List[Dict[str, str]] = None) -> List[Dict[str, Any]]:
        """
        Retrieves relevant documents from the RAG system based on the query and conversation history.
        Filters by predefined risk management datasets.

        Args:
            query (str): The current user query.
            conversation_history (List[Dict[str, str]]): List of past turns in the conversation.

        Returns:
            List[Dict[str, Any]]: A list of retrieved documents.
        """
        full_query_context = query
        if conversation_history:
            history_str = "\n".join([f"{turn['role']}: {turn['content']}" for turn in conversation_history])
            full_query_context = f"{history_str}\nUser: {query}"
        
        retrieved_documents = []
        try:
            rag_results = rag_search(query=full_query_context, k=5)

            if rag_results:
                for doc in rag_results:
                    source_dataset = doc['metadata'].get('source_dataset')
                    # Only append if the source_dataset is in our RAG_DATASETS config (without .json extension)
                    if source_dataset and source_dataset.replace('.json', '') in RAG_DATASETS:
                        retrieved_documents.append(doc)

        except Exception as e:
            print(f"An error occurred during RAG search in RAGConnector: {e}")
        
        return retrieved_documents

    def extract_similar_cases_and_evidence(self, retrieved_documents: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Processes retrieved documents to extract similar cases and evidence sources.
        """
        similar_cases = []
        evidence_sources = []
        
        for doc in retrieved_documents:
            document_content = doc.get('document', '')
            metadata = doc.get('metadata', {})
            
            # Simple heuristic for similar cases: look for "사례" or "case" in content
            if "사례" in document_content or "case" in document_content.lower():
                similar_cases.append({
                    "content": document_content,
                    "source": metadata.get('source_dataset', 'unknown'),
                    "topic": metadata.get('topic', [])
                })
            
            source_info = metadata.get('source_dataset', 'Unknown Source')
            if source_info not in evidence_sources:
                evidence_sources.append(source_info)
                
        return {
            "similar_cases": similar_cases,
            "evidence_sources": evidence_sources
        }

# Example Usage (for testing)
if __name__ == '__main__':
    settings = get_settings()
    if not settings.upstage_api_key:
        print("UPSTAGE_API_KEY is not set. RAGConnector will not function properly.")
        exit()

    connector = RAGConnector()
    
    print("\n--- RAG Connector Test ---")
    
    test_query = "선적 지연으로 인한 클레임 발생 시 유사 사례와 대처 방안이 궁금합니다."
    
    print(f"Query: '{test_query}'")
    retrieved_docs = connector.get_risk_documents(test_query)
    print(f"Retrieved {len(retrieved_docs)} documents.")
    
    extracted_info = connector.extract_similar_cases_and_evidence(retrieved_docs)
    
    print("\nSimilar Cases:")
    for case in extracted_info['similar_cases']:
        print(f"- {case['content'][:50]}... (Source: {case['source']})")
        
    print("\nEvidence Sources:")
    for source in extracted_info['evidence_sources']:
        print(f"- {source}")