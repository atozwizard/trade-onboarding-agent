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

class MistakeAgent:
    """
    MistakeAgent class for detecting possible employee mistakes and providing guidance.
    """
    agent_type: str = "mistake"
    system_prompt: str = ""

    def __init__(self):
        self.system_prompt = _load_prompt("mistake_prompt.txt")
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
        Detects possible employee mistakes based on user input and context,
        and provides explanations and prevention strategies.
        Uses RAG to find relevant information and calls Upstage Solar Pro2 LLM.

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
                print("Skipping RAG search: UPSTAGE_API_KEY is not set.")
            else:
                rag_query = user_input
                if context.get("document_type"):
                    rag_query += f" {context['document_type']} 오류"
                if context.get("user_role"):
                    rag_query += f" {context['user_role']}"
                
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
                    final_response = parsed_llm_response.get("mistake_prediction_response", llm_response_content)
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
    settings = get_settings()
    if not settings.upstage_api_key:
        print("UPSTAGE_API_KEY is not set in your .env file. RAG/LLM calls will be skipped.")
    if settings.langsmith_tracing and not settings.langsmith_api_key:
        print("LANGSMITH_API_KEY is not set. Langsmith tracing will be disabled.")
    
    print("--- Mistake Agent Test with real LLM/RAG integration ---")
    mistake_agent = MistakeAgent()
    
    test_user_input = "선적 서류 작성 중입니다. 어떤 실수를 주의해야 할까요?"
    test_context = {
        "document_type": "BL draft",
        "user_role": "junior",
        "related_process": "documentation_preparation"
    }
    
    print(f"\nRunning with UPSTAGE_API_KEY: {'*****' + settings.upstage_api_key[-4:] if settings.upstage_api_key else 'Not Set'}")
    print(f"Langsmith Tracing: {settings.langsmith_tracing and bool(settings.langsmith_api_key)}")

    result = mistake_agent.run(test_user_input, test_context)
    
    print("\n--- Mistake Agent Run Result ---")
    print(f"Response: {result['response']}")
    print(f"Agent Type: {result['agent_type']}")
    print(f"Metadata: {json.dumps(result['metadata'], indent=2, ensure_ascii=False)}")
    
    assert result['agent_type'] == "mistake"
    assert isinstance(result['response'], str)
    assert isinstance(result['metadata'], dict)
    assert result['metadata']['used_rag'] is not None
    assert isinstance(result['metadata']['documents'], list)
    assert result['metadata']['model'] == "solar-pro2"
    assert "llm_input_prepared" in result['metadata']
    print("\nMistake Agent integration test passed (if API key was valid and call succeeded)!")