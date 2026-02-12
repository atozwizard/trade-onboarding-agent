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

class EmailAgent:
    """
    EmailAgent class for analyzing business email intent/risk and drafting emails.
    """
    agent_type: str = "email"
    system_prompt: str = ""

    def __init__(self):
        self.system_prompt = _load_prompt("email_prompt.txt")
        self.settings = get_settings()

    def run(self, user_input: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Analyzes business email intent/risk or drafts emails based on user input and context.
        Uses RAG to find relevant information and prepares an LLM-ready input structure.

        Args:
            user_input (str): The user's query (e.g., "Draft an email about shipment delay")
                              or an email draft for analysis.
            context (Optional[Dict[str, Any]]): Additional context, potentially including
                                       recipient info, desired tone, etc.

        Returns:
            Dict[str, Any]: A dictionary containing the agent's response, type, and metadata.
                            {
                                "response": str,       # user-facing message
                                "agent_type": str,     # "email"
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

            # Search for relevant email examples, terminology, or risk analysis documents
            rag_query = user_input
            if context.get("email_subject"):
                rag_query += f" {context['email_subject']}"
            if context.get("recipient_type"):
                rag_query += f" {context['recipient_type']}"
            
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
                rag_context_str += f"문서 {i+1} (출처: {doc['metadata'].get('source_dataset', 'unknown')} | 주제: {', '.join(doc['metadata'].get('topic', []))}):\n{doc['document']}\n\n"
        
        llm_user_message = f"사용자 요청: {user_input}"
        if context:
            llm_user_message += f"\n추가 컨텍스트: {json.dumps(context, ensure_ascii=False)}"
        llm_user_message += rag_context_str

        # --- LLM Call Stub (Simulated Response) ---
        if "draft" in user_input.lower() or "써줘" in user_input:
            simulated_response_text = "이메일 초안이 작성되었습니다. 상황과 수신자에 맞춰 수정해 주세요."
            simulated_risk_signals = ["None"]
            simulated_urgency = "normal"
            simulated_intent = "draft_email"
            simulated_email_content = f"제목: [Draft] {context.get('email_subject', '문의')}\n\n" \
                                      f"내용: {user_input}에 대한 이메일입니다."
        else:
            simulated_response_text = "제공된 이메일에 대한 리스크 분석 결과입니다."
            simulated_risk_signals = ["hidden_dissatisfaction", "negotiation_pressure"]
            simulated_urgency = "high"
            simulated_intent = "analyze_email"
            simulated_email_content = f"분석 대상: {user_input}"

        llm_output_simulation = {
            "email_response": simulated_response_text,
            "risk_signals_assessment": simulated_risk_signals,
            "urgency_assessment": simulated_urgency,
            "detected_intent": simulated_intent,
            "simulated_email_content": simulated_email_content,
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

        response_message = f"{llm_output_simulation.get('email_response', '이메일 에이전트가 응답을 생성했습니다.')} (System prompt loaded, LLM input structured, RAG: {used_rag})"

        return {
            "response": response_message,
            "agent_type": self.agent_type,
            "metadata": metadata
        }

if __name__ == '__main__':
    settings = get_settings()
    if not settings.upstage_api_key:
        print("UPSTAGE_API_KEY is not set in your .env file. RAG search will be skipped.")

    print("--- Email Agent Test ---")
    email_agent = EmailAgent()
    
    # Test case 1: Draft email with RAG
    test_user_input_draft = "선적 지연에 대해 거래처에 보낼 정중한 이메일을 써줘."
    test_context_draft = {
        "email_subject": "선적 지연 통보",
        "recipient_type": "Client",
        "delay_reason": "악천후"
    }
    result_draft = email_agent.run(test_user_input_draft, test_context_draft)
    
    print("\n--- Email Agent Draft Test Result ---")
    print(f"Response: {result_draft['response']}")
    print(f"Agent Type: {result_draft['agent_type']}")
    print(f"Metadata: {json.dumps(result_draft['metadata'], indent=2, ensure_ascii=False)}")
    
    assert result_draft['agent_type'] == "email"
    assert "이메일 초안이 작성되었습니다" in result_draft['response']
    assert result_draft['metadata']['llm_output_simulation']['detected_intent'] == "draft_email"
    print("\nEmail Agent draft stub test passed!")

    # Test case 2: Analyze email with RAG
    test_user_input_analyze = "확인 메일: 'Your recent request seems challenging. We need to discuss further.' 이 메일의 숨겨진 위험을 분석해줘."
    test_context_analyze = {
        "recipient_type": "Supplier",
        "previous_interaction": "negotiation on price"
    }
    result_analyze = email_agent.run(test_user_input_analyze, test_context_analyze)

    print("\n--- Email Agent Analyze Test Result ---")
    print(f"Response: {result_analyze['response']}")
    print(f"Agent Type: {result_analyze['agent_type']}")
    print(f"Metadata: {json.dumps(result_analyze['metadata'], indent=2, ensure_ascii=False)}")
    
    assert result_analyze['agent_type'] == "email"
    assert "리스크 분석 결과입니다" in result_analyze['response']
    assert result_analyze['metadata']['llm_output_simulation']['detected_intent'] == "analyze_email"
    assert "hidden_dissatisfaction" in result_analyze['metadata']['llm_output_simulation']['risk_signals_assessment']
    print("\nEmail Agent analyze stub test passed!")
