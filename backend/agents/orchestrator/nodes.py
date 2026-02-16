# backend/agents/orchestrator/nodes.py

import os
import sys
import json
import uuid
import time
from typing import Dict, Any, List, Optional, Type, cast

import openai
from openai import OpenAI
from langsmith import traceable # traceable will be applied at graph level or individual agent level if needed

# External imports
from backend.config import get_settings
from backend.core.response_converter import normalize_response

# Internal imports for Orchestrator package
from .state import OrchestratorGraphState

from backend.agents.default_chat.default_chat_agent import DefaultChatAgent # Actual DefaultChatAgent import
from backend.agents.riskmanaging.graph import RiskManagingAgent # Actual RiskManagingAgent import
from backend.agents.quiz_agent.quiz_agent import QuizAgent                   # Actual QuizAgent import
from backend.agents.email_agent.email_agent import EmailAgent               # Actual EmailAgent import


# --- In-Memory Conversation Store (from old orchestrator.py) ---
class InMemoryConversationStore:
    _store: Dict[str, Dict[str, Any]] = {}

    def get_state(self, session_id: str) -> Optional[Dict[str, Any]]:
        return self._store.get(session_id)

    def save_state(self, session_id: str, state: Dict[str, Any]):
        self._store[session_id] = state

    def delete_state(self, session_id: str):
        if session_id in self._store:
            del self._store[session_id]

    def create_new_session_id(self) -> str:
        return str(uuid.uuid4())


# --- Prompt Loader Function (from old orchestrator.py) ---
def _load_prompt(prompt_file_name: str) -> str:
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # from backend/agents/orchestrator to project root
    project_root = os.path.abspath(os.path.join(current_dir, '..', '..', '..'))
    prompt_path = os.path.join(project_root, 'backend', 'prompts', prompt_file_name) # Adjusted path
    
    if not os.path.exists(prompt_path):
        raise FileNotFoundError(f"Prompt file not found: {prompt_path}")
        
    with open(prompt_path, 'r', encoding='utf-8') as f:
        return f.read()




AGENT_CLASS_MAPPING: Dict[str, Type[Any]] = {
    "riskmanaging": RiskManagingAgent,
    "quiz": QuizAgent, 
    "email": EmailAgent,
    "default_chat": DefaultChatAgent,
}

DEFAULT_AGENT_NAME = "default_chat"

# --- Global Components ---
# These components are initialized once and used across nodes.
# In a real application, these might be managed by a dependency injection framework or passed explicitly.
class OrchestratorComponents:
    def __init__(self):
        self.settings = get_settings()
        self.conversation_store = InMemoryConversationStore()
        
        self.llm = None
        if self.settings.upstage_api_key:
            self.llm = OpenAI(
                base_url="https://api.upstage.ai/v1",
                api_key=self.settings.upstage_api_key
            )
        else:
            print("Warning: UPSTAGE_API_KEY is not set. LLM calls for Orchestrator intent classification will fail.")
        
        self.orchestrator_intent_prompt = _load_prompt("orchestrator_intent_prompt.txt")

        # Configure Langsmith tracing
        if self.settings.langsmith_tracing and self.settings.langsmith_api_key:
            os.environ["LANGCHAIN_TRACING_V2"] = "true"
            os.environ["LANGCHAIN_API_KEY"] = self.settings.langsmith_api_key
            os.environ["LANGCHAIN_PROJECT"] = self.settings.langsmith_project
        else:
            os.environ["LANGCHAIN_TRACING_V2"] = "false"
        
        self.agents_instances: Dict[str, Any] = {}
        for agent_name, agent_class in AGENT_CLASS_MAPPING.items():
            self.agents_instances[agent_name] = agent_class()
            print(f"Orchestrator initialized agent: {agent_name}")

ORCHESTRATOR_COMPONENTS = OrchestratorComponents()


# --- Orchestrator Node Functions ---

def load_session_state_node(state: OrchestratorGraphState) -> Dict[str, Any]:
    # Need to convert TypedDict to dict for manipulation
    state_dict = cast(Dict[str, Any], state)
    
    session_id = state_dict["session_id"]
    conversation_store = ORCHESTRATOR_COMPONENTS.conversation_store
    
    session_data = conversation_store.get_state(session_id)
    if not session_data:
        session_data = {
            "active_agent": None,
            "conversation_history": [],
            "agent_specific_state": {},
            "last_interaction_timestamp": time.time(),
        }
        print(f"Initialized new session: {session_id}")
    else:
        print(f"Loaded existing session: {session_id}, active_agent: {session_data.get('active_agent')}")
    
    # Update state with loaded session data
    state_dict["conversation_history"] = session_data["conversation_history"]
    state_dict["active_agent"] = session_data["active_agent"]
    state_dict["agent_specific_state"] = session_data["agent_specific_state"]
    # state_dict["last_interaction_timestamp"] = session_data["last_interaction_timestamp"] # Handled by update node

    return state_dict


def _classify_intent_with_llm(user_input: str) -> str:
    llm = ORCHESTRATOR_COMPONENTS.llm
    orchestrator_intent_prompt = ORCHESTRATOR_COMPONENTS.orchestrator_intent_prompt

    if not llm:
        print("LLM client not initialized. Falling back to default.")
        return DEFAULT_AGENT_NAME
    
    try:
        system_message_content = orchestrator_intent_prompt.split('---')[0].strip()
        user_message_content = f"사용자 요청: {user_input}"

        messages = [
            {"role": "system", "content": system_message_content},
            {"role": "user", "content": user_message_content}
        ]
        
        print(f"DEBUG: LLM Intent Classification Messages: {json.dumps(messages, ensure_ascii=False, indent=2)}")

        response = llm.chat.completions.create(
            model="solar-pro2",
            messages=messages,
            temperature=0.1,
            response_format={"type": "json_object"}
        ).choices[0].message.content
        
        print(f"DEBUG: LLM Raw Intent Classification Response: {response}")
        
        parsed_response = json.loads(response)
        agent_type = parsed_response.get("agent_type", DEFAULT_AGENT_NAME)
        reason = parsed_response.get("reason", "LLM based classification.")
        print(f"LLM classified intent: {agent_type} (Reason: {reason})")
        return agent_type

    except Exception as e:
        print(f"Error during LLM intent classification: {e}. Falling back to default.")
        return DEFAULT_AGENT_NAME


def detect_intent_and_route_node(state: OrchestratorGraphState) -> Dict[str, Any]:
    state_dict = cast(Dict[str, Any], state)

    user_input = state_dict["user_input"]
    current_session_state = { # Reconstruct current_session_state for _detect_intent_and_route logic
        "active_agent": state_dict["active_agent"],
        "agent_specific_state": state_dict["agent_specific_state"],
        "conversation_history": state_dict["conversation_history"]
    }
    context = state_dict["context"]
    agents_instances = ORCHESTRATOR_COMPONENTS.agents_instances

    # 1. Prioritize active agent in session state
    active_agent_name = current_session_state.get("active_agent")
    if active_agent_name and active_agent_name in agents_instances:
        agent_specific_state = current_session_state.get("agent_specific_state", {})
        if active_agent_name == "riskmanaging":
            if agent_specific_state.get("analysis_in_progress"):
                print(f"Orchestrator continuing with active agent: {active_agent_name} (analysis in progress)")
                state_dict["selected_agent_name"] = active_agent_name
                return state_dict # Return updated state to flow to call_agent_node
        else:
            print(f"Orchestrator continuing with active agent: {active_agent_name}")
            state_dict["selected_agent_name"] = active_agent_name
            return state_dict # Return updated state

    # 2. 강력한 키워드 기반 우선 라우팅
    risk_keywords = ["클레임", "선적 지연", "리스크", "손해배상", "대처 방안", "유사 사례"]
    if any(keyword in user_input for keyword in risk_keywords):
        print(f"Orchestrator routed by Keyword Match to riskmanaging")
        state_dict["selected_agent_name"] = "riskmanaging"
        return state_dict

    # 3. Explicit mode from frontend context
    if context.get("mode") and context["mode"] in agents_instances:
        print(f"Orchestrator routing overridden by frontend context.mode to {context['mode']}")
        state_dict["selected_agent_name"] = context["mode"]
        return state_dict

    # 4. LLM-based intent classification
    llm_predicted_agent_type = _classify_intent_with_llm(user_input)
    state_dict["llm_intent_classification"] = {"predicted_type": llm_predicted_agent_type}
    
    if llm_predicted_agent_type == "out_of_scope":
        print(f"LLM classified intent as 'out_of_scope'. Routing to {DEFAULT_AGENT_NAME}.")
        state_dict["selected_agent_name"] = DEFAULT_AGENT_NAME
        return state_dict
    elif llm_predicted_agent_type in AGENT_CLASS_MAPPING:
        print(f"Orchestrator routed by LLM intent classification to {llm_predicted_agent_type}")
        state_dict["selected_agent_name"] = llm_predicted_agent_type
        return state_dict
    else:
        print(f"LLM predicted unknown agent type '{llm_predicted_agent_type}'. Falling back to default.")
        state_dict["selected_agent_name"] = DEFAULT_AGENT_NAME
        return state_dict


def call_agent_node(state: OrchestratorGraphState) -> Dict[str, Any]:
    state_dict = cast(Dict[str, Any], state)

    selected_agent_name = state_dict["selected_agent_name"]
    user_input = state_dict["user_input"]
    conversation_history = state_dict["conversation_history"]
    agent_specific_state = state_dict["agent_specific_state"]
    context = state_dict["context"]
    agents_instances = ORCHESTRATOR_COMPONENTS.agents_instances

    agent_instance = agents_instances.get(selected_agent_name)

    if not agent_instance:
        response_content = f"죄송합니다. 현재 '{selected_agent_name}' 에이전트는 사용할 수 없습니다."
        response_payload = {
            "response": response_content,
            "agent_type": "orchestrator",
            "metadata": {"reason": "Agent not found or initialized"}
        }
        state_dict["orchestrator_response"] = response_payload
        state_dict["conversation_history"].append({"role": "Agent", "content": response_content})
        state_dict["active_agent"] = None
        state_dict["agent_specific_state"] = {}
        return state_dict
    
    agent_output = agent_instance.run(
        user_input=user_input,
        conversation_history=conversation_history,
        analysis_in_progress=agent_specific_state.get("analysis_in_progress", False),
        context=context
    )

    state_dict["orchestrator_response"] = agent_output.get("response", {"response": "에이전트 응답 오류", "agent_type": "orchestrator", "metadata": {}})
    state_dict["conversation_history"] = agent_output.get("conversation_history", conversation_history)
    
    if "analysis_in_progress" in agent_output:
        state_dict["agent_specific_state"]["analysis_in_progress"] = agent_output["analysis_in_progress"]
    
    if selected_agent_name == "riskmanaging" and not state_dict["agent_specific_state"].get("analysis_in_progress"):
         state_dict["active_agent"] = None
         print(f"RiskManagingAgent completed analysis. Resetting active_agent for session {state_dict['session_id']}.")
    else:
        state_dict["active_agent"] = selected_agent_name

    return state_dict


def finalize_and_save_state_node(state: OrchestratorGraphState) -> Dict[str, Any]:
    state_dict = cast(Dict[str, Any], state)

    session_id = state_dict["session_id"]
    conversation_store = ORCHESTRATOR_COMPONENTS.conversation_store
    
    # Save session state after agent interaction
    session_state_to_save = {
        "active_agent": state_dict["active_agent"],
        "conversation_history": state_dict["conversation_history"],
        "agent_specific_state": state_dict["agent_specific_state"],
        "last_interaction_timestamp": time.time(), # Update timestamp
    }
    conversation_store.save_state(session_id, session_state_to_save)
    
    return state_dict # Return the updated state, graph will then pass to normalizer


def normalize_response_node(state: OrchestratorGraphState) -> Dict[str, Any]:
    state_dict = cast(Dict[str, Any], state)
    
    response_payload = state_dict["orchestrator_response"]
    final_response = normalize_response(response_payload)
    
    return final_response # This is the final output of the graph, to be returned by the API

