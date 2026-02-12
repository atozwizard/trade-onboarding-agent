import os
import sys
import json
from typing import Dict, Any, List, Optional

# Ensure backend directory is in path for imports
# This is usually handled at the application entry point, but included here for standalone testing
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from backend.config import get_settings
from backend.rag.embedder import get_embedding
from backend.rag.retriever import search as rag_search # Rename to avoid conflict if agent has its own search

def _load_prompt(prompt_file_name: str) -> str:
    """
    Loads a prompt text from the specified file name.
    Assumes prompt files are in backend/prompts/ relative to the project root.
    """
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(current_dir, '..', '..'))
    prompt_path = os.path.join(project_root, 'backend', 'prompts', prompt_file_name)
    
    if not os.path.exists(prompt_path):
        raise FileNotFoundError(f"Prompt file not found: {prompt_path}")
        
    with open(prompt_path, 'r', encoding='utf-8') as f:
        return f.read()

class CEOAgent:
    """
    CEOAgen class for simulating executive decision-making.
    """
    agent_type: str = "ceo"
    system_prompt: str = ""

    def __init__(self):
        self.system_prompt = _load_prompt("ceo_prompt.txt")
        self.settings = get_settings() # Load settings once

    def run(self, user_input: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Simulates executive decision-making based on the provided user input and context.
        Uses RAG to find relevant information and prepares an LLM-ready input structure.

        Args:
            user_input (str): The user's query or description of the situation.
            context (Optional[Dict[str, Any]]): Additional context for decision-making.

        Returns:
            Dict[str, Any]: A dictionary containing the agent's response, type, and metadata.
                            {
                                "response": str,       # user-facing message
                                "agent_type": str,     # "ceo"
                                "metadata": dict       # structured extra data
                            }
        """
        if context is None:
            context = {}

        # --- RAG Search ---
        retrieved_documents = []
        used_rag = False
        
        try:
            # First, check if API key is available for embedding
            if not self.settings.upstage_api_key:
                raise ValueError("UPSTAGE_API_KEY is not set. Cannot perform RAG search.")

            # Perform RAG search using user_input
            # For CEO, we might want broader search or filtered by specific topics/roles later
            # For now, a general search based on user_input
            rag_results = rag_search(query=user_input, k=3)
            
            if rag_results:
                used_rag = True
                retrieved_documents = [{"document": doc["document"], "metadata": doc["metadata"]} for doc in rag_results]
                
        except ValueError as e:
            print(f"RAG search skipped due to configuration error: {e}")
        except Exception as e:
            print(f"An error occurred during RAG search: {e}")
        
        # --- Prepare LLM Input ---
        # Construct a comprehensive user message for the LLM
        # This part would integrate retrieved_documents and context more deeply in a real scenario
        
        rag_context_str = ""
        if used_rag and retrieved_documents:
            rag_context_str = "\n\n--- 참조 문서 ---\n"
            for i, doc in enumerate(retrieved_documents):
                rag_context_str += f"문서 {i+1} (출처: {doc['metadata'].get('source_dataset', 'unknown')} | 주제: {', '.join(doc['metadata'].get('topic', []))}):\n{doc['document']}\n\n"
        
        llm_user_message = f"사용자 질문: {user_input}"
        if context:
            llm_user_message += f"\n추가 컨텍스트: {json.dumps(context, ensure_ascii=False)}"
        llm_user_message += rag_context_str

        # Placeholder for LLM interaction
        # This structure is ready for an actual LLM call
        
        # --- LLM Call Stub (Simulated Response) ---
        # The actual LLM would process self.system_prompt and llm_user_message
        # and return a structured JSON response.
        
        simulated_risk_level = "medium"
        simulated_decision = "다양한 이해관계자의 장기적인 이익을 고려하여 의사결정을 내립니다."
        simulated_reasoning = "현재 컨텍스트와 RAG 검색 결과를 바탕으로 전략적 판단을 내립니다."
        
        # Simulating LLM response based on the prompt's expected output
        llm_output_simulation = {
            "ceo_response": f"CEO 관점에서 '{user_input[:50]}...' 상황에 대한 전략적 조언입니다. {simulated_decision}.",
            "risk_level_assessment": simulated_risk_level,
            "strategic_recommendation": simulated_decision,
            "reasoning_details": simulated_reasoning,
            "used_rag_in_llm_simulation": used_rag
        }

        metadata = {
            "used_rag": used_rag,
            "documents": retrieved_documents,
            "llm_input_prepared": llm_user_message,
            "llm_output_simulation": llm_output_simulation, # Include simulated LLM output for traceability
            "input_context": context,
            "processed_input": user_input
        }

        return {
            "response": llm_output_simulation.get("ceo_response", "CEO 에이전트가 응답을 생성했습니다."),
            "agent_type": self.agent_type,
            "metadata": metadata
        }

if __name__ == '__main__':
    # Ensure UPSTAGE_API_KEY is set in .env for testing RAG and embedding
    settings = get_settings()
    if not settings.upstage_api_key:
        print("UPSTAGE_API_KEY is not set in your .env file. RAG search will be skipped.")
        # sys.exit(1) # Do not exit, just warn and let stub run

    print("--- CEO Agent Test ---")
    ceo_agent = CEOAgent()
    
    test_user_input = "선적 지연으로 클레임이 발생했습니다. 손실을 최소화하고 관계를 유지하는 방안은 무엇인가요?"
    test_context = {
        "current_situation": "shipment_delay_claim",
        "client_history": "long-term partner",
        "financial_impact_estimate": "medium"
    }
    
    result = ceo_agent.run(test_user_input, test_context)
    
    print("\n--- CEO Agent Run Result ---")
    print(f"Response: {result['response']}")
    print(f"Agent Type: {result['agent_type']}")
    print(f"Metadata: {json.dumps(result['metadata'], indent=2, ensure_ascii=False)}")
    
    assert result['agent_type'] == "ceo"
    assert "CEO 관점에서" in result['response']
    assert isinstance(result['metadata'], dict)
    assert result['metadata']['used_rag'] is not None
    assert isinstance(result['metadata']['documents'], list)
    assert "llm_input_prepared" in result['metadata']
    print("\nCEO Agent stub test passed!")
