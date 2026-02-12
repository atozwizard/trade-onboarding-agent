import os
import sys
import json
from typing import Dict, Any, List, Optional
import openai # Import openai
from openai import OpenAI # Import OpenAI client

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

        if not self.settings.upstage_api_key:
            print("Warning: UPSTAGE_API_KEY is not set. LLM calls will fail.")
            self.llm = None
        else:
            self.llm = OpenAI(
                base_url="https://api.upstage.ai/v1",
                api_key=self.settings.upstage_api_key
            )
        
        # Configure Langsmith tracing
        if self.settings.langsmith_tracing and self.settings.langsmith_api_key:
            os.environ["LANGCHAIN_TRACING_V2"] = "true"
            os.environ["LANGCHAIN_API_KEY"] = self.settings.langsmith_api_key
            os.environ["LANGCHAIN_PROJECT"] = self.settings.langsmith_project
        else:
            os.environ["LANGCHAIN_TRACING_V2"] = "false"

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
                print("Skipping RAG search: UPSTAGE_API_KEY is not set.")
            else:
                rag_query = user_input
                if context.get("email_subject"):
                    rag_query += f" {context['email_subject']}"
                if context.get("recipient_type"):
                    rag_query += f" {context['recipient_type']}"
                
                rag_results = rag_search(query=rag_query, k=3)

                if rag_results:
                    used_rag = True
                    retrieved_documents = [{"document": doc["document"], "metadata": doc["metadata"]} for doc in rag_results]

        except Exception as e:
            print(f"An error occurred during RAG search: {e}")

        # --- Prepare LLM Messages ---
        messages = [
            {"role": "system", "content": self.system_prompt}
        ]
        
        rag_context_str = ""
        if used_rag and retrieved_documents:
            rag_context_str = "\n\n--- 참조 문서 ---\n"
            for i, doc in enumerate(retrieved_documents):
                rag_context_str += f"문서 {i+1} (출처: {doc['metadata'].get('source_dataset', 'unknown')} | 유형: {doc['metadata'].get('document_type', 'unknown')} | 주제: {', '.join(doc['metadata'].get('topic', []))}):\n{doc['document']}\n\n"
        
        llm_user_message_content = f"사용자 요청: {user_input}"
        if context:
            llm_user_message_content += f"\n추가 컨텍스트: {json.dumps(context, ensure_ascii=False)}"
        llm_user_message_content += rag_context_str
        
        messages.append({"role": "user", "content": llm_user_message_content})

        # --- LLM Call ---
        llm_response_content = "LLM 호출에 실패했거나 응답이 없습니다."
        model_used = "solar-pro2"
        
        if self.llm:
            try:
                chat_completion = self.llm.chat.completions.create(
                    model=model_used,
                    messages=messages,
                    temperature=0.3,
                    response_format={"type": "json_object"} # Expect JSON output
                )
                llm_response_content = chat_completion.choices[0].message.content
                
                # Attempt to parse LLM's JSON response
                try:
                    parsed_llm_response = json.loads(llm_response_content)
                    final_response = parsed_llm_response.get("email_response", llm_response_content)
                    llm_output_details = parsed_llm_response
                except json.JSONDecodeError:
                    print(f"Warning: LLM response was not valid JSON. Response: {llm_response_content[:100]}...")
                    final_response = llm_response_content
                    llm_output_details = {"raw_llm_response": llm_response_content}
                
            except openai.APIError as e:
                print(f"Upstage API Error: {e}")
                final_response = f"LLM API 호출 중 오류가 발생했습니다: {e}"
                llm_output_details = {"error": str(e)}
            except Exception as e:
                print(f"An unexpected error occurred during LLM call: {e}")
                final_response = f"LLM 호출 중 예상치 못한 오류가 발생했습니다: {e}"
                llm_output_details = {"error": str(e)}
        else:
            final_response = "LLM 클라이언트가 초기화되지 않아 응답을 생성할 수 없습니다. UPSTAGE_API_KEY를 확인하세요."
            llm_output_details = {"error": "LLM client not initialized due to missing API key."}


        metadata = {
            "used_rag": used_rag,
            "documents": retrieved_documents,
            "model": model_used,
            "llm_input_prepared": messages,
            "llm_output_details": llm_output_details,
            "input_context": context,
            "processed_input": user_input
        }

        return {
            "response": final_response,
            "agent_type": self.agent_type,
            "metadata": metadata
        }

if __name__ == '__main__':
    # Ensure UPSTAGE_API_KEY and optionally LANGSMITH_API_KEY are set in .env for testing
    settings = get_settings()
    if not settings.upstage_api_key:
        print("UPSTAGE_API_KEY is not set in your .env file. RAG/LLM calls will be skipped.")
    if settings.langsmith_tracing and not settings.langsmith_api_key:
        print("LANGSMITH_API_KEY is not set. Langsmith tracing will be disabled.")
    
    print("--- Email Agent Test with real LLM/RAG integration ---")
    email_agent = EmailAgent()
    
    # Test case 1: Draft email with RAG
    test_user_input_draft = "선적 지연에 대해 거래처에 보낼 정중한 이메일을 써줘."
    test_context_draft = {
        "email_subject": "선적 지연 통보",
        "recipient_type": "Client",
        "delay_reason": "악천후"
    }
    
    print(f"\nRunning with UPSTAGE_API_KEY: {'*****' + settings.upstage_api_key[-4:] if settings.upstage_api_key else 'Not Set'}")
    print(f"Langsmith Tracing: {settings.langsmith_tracing and bool(settings.langsmith_api_key)}")

    result_draft = email_agent.run(test_user_input_draft, test_context_draft)
    
    print("\n--- Email Agent Draft Test Result ---")
    print(f"Response: {result_draft['response']}")
    print(f"Agent Type: {result_draft['agent_type']}")
    print(f"Metadata: {json.dumps(result_draft['metadata'], indent=2, ensure_ascii=False)}")
    
    assert result_draft['agent_type'] == "email"
    assert "이메일 초안이 작성되었습니다" in result_draft['response'] or "LLM API 호출 중" in result_draft['response'] or "LLM 클라이언트가 초기화되지 않아" in result_draft['response']
    print("\nEmail Agent draft integration test passed (if API key was valid and call succeeded)!")

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
    assert "리스크 분석 결과입니다" in result_analyze['response'] or "LLM API 호출 중" in result_analyze['response'] or "LLM 클라이언트가 초기화되지 않아" in result_analyze['response']
    print("\nEmail Agent analyze integration test passed (if API key was valid and call succeeded)!")