# backend/agents/email_agent/nodes.py

import os
import sys
import json
from typing import Dict, Any, List, Optional, cast
import openai
from openai import OpenAI

# Ensure backend directory is in path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '..', '..', '..')) # From backend/agents/email_agent to project root
sys.path.append(project_root)

# Local imports
from backend.config import get_settings
# RAG and validation functionality now provided by tools.py
from backend.agents.email_agent.state import EmailGraphState

# --- Constants ---
EMAIL_AGENT_TYPE = "email"

# --- Prompt Loader Function ---
def _load_prompt(prompt_file_name: str) -> str:
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(current_dir, '..', '..', '..')) # Correct path
    prompt_path = os.path.join(project_root, 'backend', 'prompts', prompt_file_name)
    
    if not os.path.exists(prompt_path):
        raise FileNotFoundError(f"Prompt file not found: {prompt_path}")
        
    with open(prompt_path, 'r', encoding='utf-8') as f:
        return f.read()

# --- Global Components for EmailAgent ---
class EmailAgentComponents:
    def __init__(self):
        self.settings = get_settings()
        self.system_prompt = _load_prompt("email_prompt.txt")

        self.llm = None
        if self.settings.upstage_api_key:
            self.llm = OpenAI(
                base_url="https://api.upstage.ai/v1",
                api_key=self.settings.upstage_api_key
            )
        else:
            print("Warning: UPSTAGE_API_KEY is not set for EmailAgent. LLM calls will fail.")
        
        # Configure Langsmith tracing - if not configured by Orchestrator
        if self.settings.langsmith_tracing and self.settings.langsmith_api_key:
            os.environ["LANGCHAIN_TRACING_V2"] = "true"
            os.environ["LANGCHAIN_API_KEY"] = self.settings.langsmith_api_key
            os.environ["LANGCHAIN_PROJECT"] = self.settings.langsmith_project
        # else: os.environ["LANGCHAIN_TRACING_V2"] is already set to "false" by orchestrator if not enabled

EMAIL_AGENT_COMPONENTS = EmailAgentComponents()


# --- Node Functions ---

def perform_rag_search_node(state: EmailGraphState) -> Dict[str, Any]:
    state_dict = cast(Dict[str, Any], state)

    user_input = state_dict["user_input"]
    context = state_dict["context"]

    # Build search query
    rag_query = user_input
    if context.get("email_subject"):
        rag_query += f" {context['email_subject']}"
    if context.get("recipient_type"):
        rag_query += f" {context['recipient_type']}"

    # Use tool: search_email_references
    from backend.agents.email_agent.tools import search_email_references

    try:
        # Determine search type from mode
        mode = context.get("mode", "review")
        search_type = "mistakes" if mode == "review" else "all"

        retrieved_documents = search_email_references(
            query=rag_query,
            k=3,
            search_type=search_type
        )
        used_rag = len(retrieved_documents) > 0
    except Exception as e:
        print(f"Error during RAG search: {e}")
        retrieved_documents = []
        used_rag = False

    state_dict["retrieved_documents"] = retrieved_documents
    state_dict["used_rag"] = used_rag

    # Format context string
    rag_context_str = ""
    if used_rag and retrieved_documents:
        rag_context_str = "\n--- 참조 문서 ---\n"
        for i, doc in enumerate(retrieved_documents):
            metadata = doc.get("metadata", {})
            rag_context_str += f"\n문서 {i+1} (출처: {metadata.get('source_dataset', 'unknown')} | 유형: {metadata.get('document_type', 'unknown')})\n"
            rag_context_str += f"{doc['document']}\n"

    state_dict["rag_context_str"] = rag_context_str

    return state_dict


def prepare_llm_messages_node(state: EmailGraphState) -> Dict[str, Any]:
    state_dict = cast(Dict[str, Any], state)

    system_prompt = EMAIL_AGENT_COMPONENTS.system_prompt
    user_input = state_dict["user_input"]
    context = state_dict["context"]
    rag_context_str = state_dict.get("rag_context_str", "")

    messages = [
        {"role": "system", "content": system_prompt}
    ]
    
    llm_user_message_content = f"사용자 요청: {user_input}"
    if context:
        llm_user_message_content += f"\n추가 컨텍스트: {json.dumps(context, ensure_ascii=False)}"
    llm_user_message_content += rag_context_str
    
    messages.append({"role": "user", "content": llm_user_message_content})

    state_dict["llm_messages"] = messages
    return state_dict


def call_llm_and_parse_response_node(state: EmailGraphState) -> Dict[str, Any]:
    state_dict = cast(Dict[str, Any], state)

    llm = EMAIL_AGENT_COMPONENTS.llm
    llm_messages = state_dict["llm_messages"]

    llm_response_content = "LLM 호출에 실패했거나 응답이 없습니다."
    model_used = "solar-pro2"
    llm_output_details = {}
    
    if llm:
        try:
            chat_completion = llm.chat.completions.create(
                model=model_used,
                messages=llm_messages,
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            llm_response_content = chat_completion.choices[0].message.content
            state_dict["llm_raw_response_content"] = llm_response_content
            
            try:
                parsed_llm_response = json.loads(llm_response_content)
                final_response_content = parsed_llm_response.get("email_response", llm_response_content)
                llm_output_details = parsed_llm_response
            except json.JSONDecodeError:
                print(f"Warning: LLM response was not valid JSON. Response: {llm_response_content[:100]}...")
                final_response_content = llm_response_content
                llm_output_details = {"raw_llm_response": llm_response_content}
            
        except openai.APIError as e:
            print(f"Upstage API Error: {e}")
            final_response_content = f"LLM API 호출 중 오류가 발생했습니다: {e}"
            llm_output_details = {"error": str(e)}
        except Exception as e:
            print(f"An unexpected error occurred during LLM call: {e}")
            final_response_content = f"LLM 호출 중 예상치 못한 오류가 발생했습니다: {e}"
            llm_output_details = {"error": str(e)}
    else:
        final_response_content = "LLM 클라이언트가 초기화되지 않아 응답을 생성할 수 없습니다. UPSTAGE_API_KEY를 확인하세요."
        llm_output_details = {"error": "LLM client not initialized due to missing API key."}

    state_dict["final_response_content"] = final_response_content
    state_dict["llm_output_details"] = llm_output_details
    state_dict["model_used"] = model_used # Store model used for metadata
    return state_dict


def format_email_output_node(state: EmailGraphState) -> Dict[str, Any]:
    state_dict = cast(Dict[str, Any], state)

    final_response = state_dict["final_response_content"]
    used_rag = state_dict.get("used_rag", False)
    retrieved_documents = state_dict.get("retrieved_documents", [])
    model_used = state_dict.get("model_used", "solar-pro2")
    llm_messages = state_dict.get("llm_messages", [])
    llm_output_details = state_dict.get("llm_output_details", {})
    context = state_dict["context"]
    user_input = state_dict["user_input"]


    metadata = {
        "used_rag": used_rag,
        "documents": retrieved_documents,
        "model": model_used,
        "llm_input_prepared": llm_messages,
        "llm_output_details": llm_output_details,
        "input_context": context,
        "processed_input": user_input
    }

    state_dict["agent_output_for_orchestrator"] = {
        "response": final_response,
        "agent_type": EMAIL_AGENT_TYPE,
        "metadata": metadata
    }
    return state_dict
