# backend/agents/riskmanaging/rag_connector.py

from typing import List, Dict, Any, Optional
import os
import sys

# Ensure backend directory is in path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '..', '..', '..')) # Go up three levels to reach backend
sys.path.append(project_root)

from backend.config import get_settings
from backend.rag.retriever import search_with_filter # Changed import
from backend.agents.riskmanaging.config import RAG_DATASETS

# Constant for number of results per filtered search
DEFAULT_RAG_K_PER_TYPE = 3 # Retrieve 3 documents for each RAG_DATASET type

class RAGConnector:
    def __init__(self):
        self.settings = get_settings()
        if not self.settings.upstage_api_key:
            print("Warning: UPSTAGE_API_KEY is not set. RAG searches may not function.")

    def get_risk_documents(self, query: str, conversation_history: List[Dict[str, str]] = None) -> List[Dict[str, Any]]:
        """
        Retrieves relevant documents from the RAG system based on the query and conversation history.
        Filters by predefined risk management datasets.
        
        This now iterates through RAG_DATASETS and calls search_with_filter for each.

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
        unique_docs = set() # To store unique document contents and avoid duplicates

        try:
            # Iterate through the RAG_DATASETS defined in config and filter by document_type
            for doc_type_filter in RAG_DATASETS:
                print(f"RAGConnector: Searching with document_type='{doc_type_filter}' for query: {full_query_context[:50]}...")
                # Use search_with_filter instead of search
                rag_results_for_type = search_with_filter(
                    query=full_query_context, 
                    k=DEFAULT_RAG_K_PER_TYPE, 
                    document_type=doc_type_filter
                )

                if rag_results_for_type:
                    for doc in rag_results_for_type:
                        # Add only if not already in the list (based on document content)
                        doc_content = doc.get('document')
                        if doc_content and doc_content not in unique_docs:
                            retrieved_documents.append(doc)
                            unique_docs.add(doc_content)
                
            print(f"RAGConnector: Retrieved {len(retrieved_documents)} unique documents after filtering by RAG_DATASETS.")

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
            # Ensure unique source info
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