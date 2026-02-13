import os
import sys
import json
import uuid
import time # For tracking last interaction
from typing import Dict, Any, List, Optional, Type
import openai # Keep for potential future LLM use
from openai import OpenAI
from langsmith import traceable

# Ensure backend directory is in path for module imports
# current_dir is backend/agents/, need to reach project root (..)
# or for modules like backend.rag.embedder (../rag)
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '..', '..', '..'))
sys.path.insert(0, project_root)


# --- Imports for Orchestrator Logic ---
from backend.config import get_settings
from backend.rag.embedder import get_embedding # For orchestrator's similarity engine
from backend.agents.riskmanaging.trigger_detector import detect_risk_trigger # For orchestrator's intent detection
from backend.agents.riskmanaging.similarity_engine import SimilarityEngine # Re-using for orchestrator's intent detection

# --- Agent Imports ---
from backend.agents.riskmanaging.riskmanaging_agent import RiskManagingAgent
# from backend.agents.quiz_agent import QuizAgent # Placeholder for other agents
# from backend.agents.email_agent import EmailAgent
# from backend.agents.mistake_agent import MistakeAgent
# from backend.agents.ceo_agent import CEOAgent


# --- In-Memory Conversation Store (Moved from deleted backend/conversation_store.py) ---
class InMemoryConversationStore:
    """
    In-memory implementation of ConversationStore.
    NOT FOR PRODUCTION USE - only for demonstration/development.
    A real system would use Redis, a database, etc.
    """
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


# --- Default Chat Agent (Moved from deleted orchestrator_config.py or for generic responses) ---
class DefaultChatAgent:
    """A simple agent for general conversation or fallback."""
    agent_type: str = "default_chat"
    def run(self, user_input: str, conversation_history: List[Dict[str, str]], analysis_in_progress: bool, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        # For a simple default agent, history is not critical for its own logic, but pass it along
        updated_history = list(conversation_history)
        updated_history.append({"role": "User", "content": user_input})
        
        response_message = f"'{user_input}' 에 대한 일반적인 답변입니다. 다른 도움이 필요하신가요?"
        updated_history.append({"role": "Agent", "content": response_message})

        return {
            "response": {
                "response": response_message,
                "agent_type": self.agent_type,
                "metadata": {}
            },
            "conversation_history": updated_history,
            "analysis_in_progress": False # Default agent never starts an 'analysis'
        }


# --- Orchestrator's Agent Routing Configuration (Moved from deleted orchestrator_config.py) ---
AGENT_CLASS_MAPPING: Dict[str, Type[Any]] = {
    "riskmanaging": RiskManagingAgent,
    "default_chat": DefaultChatAgent, # Register default chat agent
    # "quiz": QuizAgent, # Add other agents here
    # "email": EmailAgent,
    # "mistake": MistakeAgent,
    # "ceo": CEOAgent,
}

ORCHESTRATOR_AGENT_TRIGGER_MAP = {
    "riskmanaging": [
        "실수", "클레임", "지연", "문제", "리스크", "페널티", "손실", "위험", "긴급", "대응", "계약 위반", "계약"
    ],
    # "quiz": ["퀴즈", "문제", "학습", "테스트", "시험"],
    # "email": ["메일", "이메일", "작성", "보내기", "피드백"],
    # "mistake": ["실수", "오류", "예측", "방지", "가이드", "조심"],
    # "ceo": ["보고", "대표님", "CEO", "발표", "브리핑"],
}

ORCHESTRATOR_SIMILARITY_THRESHOLD = 0.82
DEFAULT_AGENT_NAME = "default_chat"


class Orchestrator:
    """
    Orchestrator class for managing conversation flow, routing to appropriate agents,
    and handling session state.
    """
    orchestrator_type: str = "orchestrator"

    def __init__(self):
        self.settings = get_settings()
        self.conversation_store = InMemoryConversationStore()
        self.similarity_engine = SimilarityEngine() # Re-using existing similarity engine

        self.agents: Dict[str, Any] = {}
        self._initialize_agents()

        # Configure Langsmith tracing - kept here for Orchestrator's own tracing
        if self.settings.langsmith_tracing and self.settings.langsmith_api_key:
            os.environ["LANGCHAIN_TRACING_V2"] = "true"
            os.environ["LANGCHAIN_API_KEY"] = self.settings.langsmith_api_key
            os.environ["LANGCHAIN_PROJECT"] = self.settings.langsmith_project
        else:
            os.environ["LANGCHAIN_TRACING_V2"] = "false"

    def _initialize_agents(self):
        """Initializes all agents defined in AGENT_CLASS_MAPPING."""
        for agent_name, agent_class in AGENT_CLASS_MAPPING.items():
            self.agents[agent_name] = agent_class()
            print(f"Orchestrator initialized agent: {agent_name}")

    def _detect_intent_and_route(self, user_input: str, current_session_state: Dict[str, Any], context: Dict[str, Any]) -> str:
        """
        Detects the user's intent and decides which agent should handle the request.
        Prioritizes existing active agent, then explicit mode, then trigger words,
        then semantic similarity, finally falling back to default.
        """
        # Initialize debug tracking variables
        matched_trigger = None
        similarity_score = None
        selected_agent = None # To be updated as routing progresses

        # DEBUG: Initial routing state
        print("ROUTING INPUT:", user_input)
        
        # 1. Explicit mode from frontend context (e.g., for dedicated buttons/flows)
        if context.get("mode") and context["mode"] in self.agents:
            selected_agent = context["mode"]
            print(f"Orchestrator routing overridden by frontend context.mode to {selected_agent}")
            # FINAL DEBUG LOGS (Mandatory - requested by user)
            print("TRIGGER MATCH:", matched_trigger)
            print("SIMILARITY:", similarity_score)
            print("FINAL ROUTE:", selected_agent)
            return selected_agent

        # 2. Trigger word detection for initial routing (FIX 3 will modify this block)
        # We need to extract the trigger word detection logic to a separate helper or integrate with the loop.
        # For now, let's keep it in loop and modify the condition.
        for agent_name, trigger_words in ORCHESTRATOR_AGENT_TRIGGER_MAP.items():
            if agent_name in self.agents: # Ensure agent is initialized
                for word in trigger_words:
                    if word in user_input: # FIX 3: Removed .lower() and in .lower()
                        selected_agent = agent_name
                        matched_trigger = word # Store for debug log
                        print(f"Orchestrator routed by trigger word '{word}' to {selected_agent}")
                        # FINAL DEBUG LOGS (Mandatory - requested by user)
                        print("TRIGGER MATCH:", matched_trigger)
                        print("SIMILARITY:", similarity_score)
                        print("FINAL ROUTE:", selected_agent)
                        return selected_agent

        # 3. Semantic similarity for initial routing
        # Check if self.similarity_engine.check_similarity supports return_score
        # For now, assume it returns a boolean. We will fetch score explicitly if needed.
        # If the user input is similar enough to risk-related topics, route to riskmanaging
        if "riskmanaging" in self.agents:
            # check_similarity now returns (is_similar, score)
            is_similar_to_risk, score = self.similarity_engine.check_similarity(user_input, ORCHESTRATOR_SIMILARITY_THRESHOLD, return_score=True)
            similarity_score = score
            if is_similar_to_risk:
                selected_agent = "riskmanaging"
                print(f"Orchestrator routed by semantic similarity to {selected_agent} (Score: {similarity_score:.2f})")
                # FINAL DEBUG LOGS (Mandatory - requested by user)
                print("TRIGGER MATCH:", matched_trigger)
                print("SIMILARITY:", similarity_score)
                print("FINAL ROUTE:", selected_agent)
                return selected_agent
            
        # 4. Active agent continuation (FIX 1: Only for riskmanaging if analysis_in_progress)
        active_agent_name = current_session_state.get("active_agent")
        if active_agent_name == "riskmanaging": # FIX 1: Only lock if risk analysis is in progress
            agent_specific_state = current_session_state.get("agent_specific_state", {})
            if agent_specific_state.get("analysis_in_progress"):
                selected_agent = "riskmanaging"
                print("Continuing riskmanaging (analysis in progress)")
                # FINAL DEBUG LOGS (Mandatory - requested by user)
                print("TRIGGER MATCH:", matched_trigger)
                print("SIMILARITY:", similarity_score)
                print("FINAL ROUTE:", selected_agent)
                return selected_agent

        # 5. Fallback to default agent
        selected_agent = DEFAULT_AGENT_NAME
        print(f"Orchestrator routed to default agent: {selected_agent}")
        # FINAL DEBUG LOGS (Mandatory - requested by user)
        print("TRIGGER MATCH:", matched_trigger)
        print("SIMILARITY:", similarity_score)
        print("FINAL ROUTE:", selected_agent)
        return selected_agent

    @traceable(name="orchestrator_run_main")
    def run(self, session_id: str, user_input: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Orchestrates the conversation flow for a given session.

        Args:
            session_id (str): Unique identifier for the current conversation session.
            user_input (str): The user's message.
            context (Optional[Dict[str, Any]]): Additional context from the frontend (e.g., mode).

        Returns:
            Dict[str, Any]: The agent's response and updated session state information for external use.
            The 'response' key will contain a dict structured like ChatResponse.
        """
        if context is None:
            context = {}
        
        # DEBUG LOGS (Mandatory - requested by user)
        print("DEBUG user_input:", user_input)
        
        # 1. Load session state
        session_state = self.conversation_store.get_state(session_id)
        print("DEBUG active_agent:", session_state.get("active_agent") if session_state else None)
        print("DEBUG context.mode:", context.get("mode"))
        if not session_state:
            session_state = {
                "active_agent": None,
                "conversation_history": [],
                "agent_specific_state": {},
                "last_interaction_timestamp": time.time(),
            }
            print(f"Initialized new session: {session_id}")
        else:
            print(f"Loaded existing session: {session_id}, active_agent: {session_state.get('active_agent')}")


        # 2. Detect intent and route to agent
        print("DEBUG trigger check start") # Mandatory debug log
        target_agent_name = self._detect_intent_and_route(user_input, session_state, context)
        
        # If switching agents, reset relevant parts of state for the new agent
        if session_state["active_agent"] != target_agent_name:
            print(f"Switching active agent from {session_state['active_agent']} to {target_agent_name}. Resetting agent_specific_state and conversation_history.")
            session_state["active_agent"] = target_agent_name
            session_state["agent_specific_state"] = {} # Clear specific state for new agent
            session_state["conversation_history"] = [] # Clear history for new agent (start fresh contextually)
        
        agent_instance = self.agents.get(target_agent_name)

        if not agent_instance:
            response_content = f"죄송합니다. 현재 '{target_agent_name}' 에이전트는 사용할 수 없습니다."
            response_payload = {
                "response": response_content,
                "agent_type": self.orchestrator_type, # Orchestrator provides fallback
                "metadata": {"reason": "Agent not found or initialized"}
            }
            session_state["conversation_history"].append({"role": "Agent", "content": response_content}) # Log orchestrator's response
            session_state["active_agent"] = None # Reset active agent if it failed
            session_state["last_interaction_timestamp"] = time.time()
            self.conversation_store.save_state(session_id, session_state)
            return response_payload


        # 3. Prepare agent-specific state and call agent
        # All agents now expect conversation_history and return updated one.
        # They also return whether they are still 'analysis_in_progress' or similar flags.
        
        current_agent_history = session_state.get("conversation_history", [])
        current_agent_specific_state = session_state.get("agent_specific_state", {})

        # RiskManagingAgent expects analysis_in_progress
        analysis_in_progress_flag = current_agent_specific_state.get("analysis_in_progress", False)
        
        # Generic call for all agents
        agent_output = agent_instance.run(
            user_input=user_input,
            conversation_history=current_agent_history,
            analysis_in_progress=analysis_in_progress_flag, # Pass if needed, agent can ignore if not applicable
            context=context
        )
        
        # Extract results from agent_output (expected format from stateless agents)
        response_payload = agent_output.get("response", {"response": "에이전트 응답 오류", "agent_type": agent_instance.agent_type, "metadata": {}})
        updated_agent_history = agent_output.get("conversation_history", current_agent_history)
        updated_analysis_in_progress = agent_output.get("analysis_in_progress", False)


        # 4. Update and Save Session State
        session_state["conversation_history"] = updated_agent_history
        session_state["agent_specific_state"]["analysis_in_progress"] = updated_analysis_in_progress
        
        # If agent signaled completion, reset active_agent so orchestrator re-evaluates next turn
        if not updated_analysis_in_progress and target_agent_name == "riskmanaging":
             session_state["active_agent"] = None
             print(f"RiskManagingAgent completed analysis. Resetting active_agent for session {session_id}.")
        
        session_state["last_interaction_timestamp"] = time.time()
        self.conversation_store.save_state(session_id, session_state)

        return {
            "response": response_payload,
            "conversation_history": updated_agent_history,
            "analysis_in_progress": updated_analysis_in_progress
        }

if __name__ == '__main__':
    # Test Orchestrator with RiskManagingAgent and DefaultChatAgent
    settings = get_settings()
    if not settings.upstage_api_key:
        print("UPSTAGE_API_KEY is not set in your .env file. LLM calls for intent detection will be skipped.")
    if settings.langsmith_tracing and not settings.langsmith_api_key:
        print("LANGSMITH_API_KEY is not set. Langsmith tracing will be disabled.")
    
    print("--- Orchestrator Test Sequence ---")
    orchestrator = Orchestrator()
    
    # Minimal test for default chat
    print("\n--- Test 1: Default Chat ---")
    session_id_default = "test_default_session"
    user_input_default = "안녕하세요, 날씨가 좋네요."
    result_default = orchestrator.run(session_id_default, user_input_default)
    print(f"  Response: {result_default['response']['response']}")
    assert result_default['response']['agent_type'] == "default_chat"
    assert "안녕하세요" in result_default['response']['response']

    # Minimal test for riskmanaging trigger
    print("\n--- Test 2: RiskManaging Trigger ---")
    session_id_risk = "test_risk_session"
    user_input_risk = "계약에 리스크가 있습니다."
    result_risk = orchestrator.run(session_id_risk, user_input_risk)
    print(f"  Response: {result_risk['response']['response']}")
    assert result_risk['response']['agent_type'] == "riskmanaging"
    assert result_risk['analysis_in_progress'] == True

    print("\n--- All basic orchestrator tests passed. ---")
