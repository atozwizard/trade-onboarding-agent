import os
import sys
import json
from typing import Dict, Any, List, Optional

# Ensure backend directory is in path for imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from backend.config import get_settings
from backend.rag.embedder import get_embedding
from backend.rag.retriever import search as rag_search

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

class MistakeAgent:
    """
    MistakeAgent class for detecting possible employee mistakes and providing guidance.
    """
    agent_type: str = "mistake"
    system_prompt: str = ""

    def __init__(self):
        self.system_prompt = _load_prompt("mistake_prompt.txt")
        self.settings = get_settings()

    def run(self, user_input: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Detects possible employee mistakes based on user input and context,
        and provides explanations and prevention strategies.
        Uses RAG to find relevant information and prepares an LLM-ready input structure.

        Args:
            user_input (str): The user's description of a situation or a request for mistake analysis.
            context (Optional[Dict[str, Any]]): Additional context, potentially including
                                       common mistake patterns, internal process documents.

        Returns:
            Dict[str, Any]: A dictionary containing the agent's response, type, and metadata.
                            {
                                "response": str,       # user-facing message
                                "agent_type": str,     # "mistake"
                                "metadata": dict       # structured extra data
                            }
        """
        if context is None:
            context = {}

        # --- RAG Search ---
        retrieved_documents = []
        used_rag = False

        try:
            if not self.settings.upstage_api_key:
                raise ValueError("UPSTAGE_API_KEY is not set. Cannot perform RAG search.")

            # Search for relevant mistake cases, internal processes, document errors
            rag_query = user_input
            if context.get("document_type"):
                rag_query += f" {context['document_type']} 오류"
            if context.get("user_role"):
                rag_query += f" {context['user_role']}"
            
            rag_results = rag_search(query=rag_query, k=3)

            if rag_results:
                used_rag = True
                retrieved_documents = [{"document": doc["document"], "metadata": doc["metadata"]} for doc in rag_results]

        except ValueError as e:
            print(f"RAG search skipped due to configuration error: {e}")
        except Exception as e:
            print(f"An error occurred during RAG search: {e}")

        # --- Prepare LLM Input ---
        rag_context_str = ""
        if used_rag and retrieved_documents:
            rag_context_str = "\n\n--- 참조 문서 ---\n"
            for i, doc in enumerate(retrieved_documents):
                rag_context_str += f"문서 {i+1} (출처: {doc['metadata'].get('source_dataset', 'unknown')} | 유형: {doc['metadata'].get('document_type', 'unknown')} | 주제: {', '.join(doc['metadata'].get('topic', []))}):\n{doc['document']}\n\n"
        
        llm_user_message = f"사용자 요청: {user_input}"
        if context:
            llm_user_message += f"\n추가 컨텍스트: {json.dumps(context, ensure_ascii=False)}"
        llm_user_message += rag_context_str

        # --- LLM Call Stub (Simulated Response) ---
        simulated_mistakes = ["BL date mismatch", "HS code error"]
        simulated_risk_level = "high"
        simulated_coaching_point = "Always double-check critical document fields."
        simulated_explanation = "BL 날짜 불일치나 HS 코드 오류는 통관 지연 및 벌금으로 이어질 수 있어 회사에 큰 재정적 손실을 입히고 거래처와의 신뢰 관계를 손상시킬 수 있습니다. 이러한 실수는 실무자의 신중한 검토 부족이나 정보 오입력으로 인해 발생하며, 내부적으로는 엄중한 비판을 받을 수 있는 중대한 사안입니다."

        llm_output_simulation = {
            "predicted_mistakes": simulated_mistakes,
            "risk_level_assessment": simulated_risk_level,
            "coaching_point_recommendation": simulated_coaching_point,
            "explanation_details": simulated_explanation,
            "used_rag_in_llm_simulation": used_rag
        }

        metadata = {
            "used_rag": used_rag,
            "documents": retrieved_documents,
            "llm_input_prepared": llm_user_message,
            "llm_output_simulation": llm_output_simulation,
            "input_context": context,
            "processed_input": user_input
        }

        response_message = f"제시된 상황 '{user_input[:50]}...'에서 발생 가능한 실수와 예방 가이드입니다. " \
                           f"예상되는 실수: {', '.join(simulated_mistakes)}. (System prompt loaded, LLM input structured, RAG: {used_rag})"

        return {
            "response": response_message,
            "agent_type": self.agent_type,
            "metadata": metadata
        }

if __name__ == '__main__':
    settings = get_settings()
    if not settings.upstage_api_key:
        print("UPSTAGE_API_KEY is not set in your .env file. RAG search will be skipped.")

    print("--- Mistake Agent Test ---")
    mistake_agent = MistakeAgent()
    
    test_user_input = "선적 서류 작성 중입니다. 어떤 실수를 주의해야 할까요?"
    test_context = {
        "document_type": "BL draft",
        "user_role": "junior",
        "related_process": "documentation_preparation"
    }
    
    result = mistake_agent.run(test_user_input, test_context)
    
    print("\n--- Mistake Agent Run Result ---")
    print(f"Response: {result['response']}")
    print(f"Agent Type: {result['agent_type']}")
    print(f"Metadata: {json.dumps(result['metadata'], indent=2, ensure_ascii=False)}")
    
    assert result['agent_type'] == "mistake"
    assert "발생 가능한 실수와 예방 가이드입니다" in result['response']
    assert isinstance(result['metadata']['llm_output_simulation']['predicted_mistakes'], list)
    assert result['metadata']['llm_output_simulation']['risk_level_assessment'] == "high"
    print("\nMistake Agent stub test passed!")
