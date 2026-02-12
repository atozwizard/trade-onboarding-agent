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
project_root = os.path.abspath(os.path.join(current_dir, '..', '..'))
sys.path.append(project_root)


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
        "실수", "클레임", "지연", "문제", "리스크", "페널티", "손실", "위험", "긴급", "대응", "계약 위반"
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
        # 1. Prioritize active agent in session state
        active_agent_name = current_session_state.get("active_agent")
        if active_agent_name and active_agent_name in self.agents:
            # Check if the active agent is still "in progress"
            agent_specific_state = current_session_state.get("agent_specific_state", {})
            if active_agent_name == "riskmanaging":
                if agent_specific_state.get("analysis_in_progress"):
                    print(f"Orchestrator continuing with active agent: {active_agent_name} (analysis in progress)")
                    return active_agent_name
            # For other agents, if they are active, continue with them unless they signal completion
            # For now, assume any active agent continues unless riskmanaging specifically sets it to False
            else:
                print(f"Orchestrator continuing with active agent: {active_agent_name}")
                return active_agent_name
        
        # 2. Explicit mode from frontend context (e.g., for dedicated buttons/flows)
        if context.get("mode") and context["mode"] in self.agents:
            print(f"Orchestrator routing overridden by frontend context.mode to {context['mode']}")
            return context["mode"]

        # 3. Trigger word detection for initial routing
        for agent_name, trigger_words in ORCHESTRATOR_AGENT_TRIGGER_MAP.items():
            if agent_name in self.agents: # Ensure agent is initialized
                for word in trigger_words:
                    if word.lower() in user_input.lower():
                        print(f"Orchestrator routed by trigger word '{word}' to {agent_name}")
                        return agent_name

        # 4. Semantic similarity for initial routing
        for agent_name in AGENT_CLASS_MAPPING.keys():
            if agent_name in self.agents and agent_name == "riskmanaging": # Currently only for riskmanaging
                is_similar_to_risk = self.similarity_engine.check_similarity(user_input, ORCHESTRATOR_SIMILARITY_THRESHOLD)
                if is_similar_to_risk:
                    print(f"Orchestrator routed by semantic similarity to {agent_name}")
                    return agent_name
            # Add specific similarity checks for other agents if necessary

        # 5. Fallback to default agent
        print(f"Orchestrator routed to default agent: {DEFAULT_AGENT_NAME}")
        return DEFAULT_AGENT_NAME

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

        # 1. Load session state
        session_state = self.conversation_store.get_state(session_id)
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

        return response_payload # This is the dict directly consumable by FastAPI ChatResponse

if __name__ == '__main__':
    # Test Orchestrator with RiskManagingAgent and DefaultChatAgent
    settings = get_settings()
    if not settings.upstage_api_key:
        print("UPSTAGE_API_KEY is not set in your .env file. LLM calls for intent detection will be skipped.")
    if settings.langsmith_tracing and not settings.langsmith_api_key:
        print("LANGSMITH_API_KEY is not set. Langsmith tracing will be disabled.")
    
    print("--- Orchestrator Test Sequence ---")
    orchestrator = Orchestrator()
    
    test_scenarios = [
        # Scenario 1: Passthrough to default agent
        {"session_id": "test_session_1", "query": "안녕하세요, 날씨가 좋네요.", "expected_agent": "default_chat"},
        
        # Scenario 2: Single-turn risk analysis (direct trigger)
        {"session_id": "test_session_2", "query": "해외 거래처로부터 선적이 1주일 지연될 것 같다고 통보받았습니다. 계약서상 3일 이상 지연 시 일당 1% 페널티가 있습니다. 어떻게 대응해야 할까요?", "expected_agent": "riskmanaging", "expect_report": True},
        
        # Scenario 3: Multi-turn risk analysis
        {"session_id": "test_session_3", "query": "신규 프로젝트 진행 중에 문제가 발생했습니다.", "expected_agent": "riskmanaging", "expect_follow_up": True},
        {"session_id": "test_session_3", "query": "납기 지연과 품질 이슈가 동시에 발생했습니다. 계약 위반 가능성도 있습니다.", "expected_agent": "riskmanaging", "expect_follow_up": True},
        {"session_id": "test_session_3", "query": "A사와의 10만 달러 규모 계약이고, 5일 이상 지연 시 일당 1%의 페널티가 있습니다. 예상 손실액은 5천 달러입니다.", "expected_agent": "riskmanaging", "expect_report": True},
        
        # Scenario 4: Switch from risk to default after completion
        {"session_id": "test_session_4", "query": "지금 리스크 분석 해줘", "expected_agent": "riskmanaging", "expect_follow_up": True},
        {"session_id": "test_session_4", "query": "납기 지연과 예상 손실액은 1000만원입니다.", "expected_agent": "riskmanaging", "expect_report": True},
        {"session_id": "test_session_4", "query": "오늘 날씨 어때?", "expected_agent": "default_chat"}, # Should switch to default

        # Scenario 5: Explicit mode override (if frontend sends context mode)
        {"session_id": "test_session_5", "query": "아무거나 말해줘.", "context": {"mode": "riskmanaging"}, "expected_agent": "riskmanaging", "expect_follow_up": True}
    ]

    for scenario in test_scenarios:
        s_id = scenario["session_id"]
        query = scenario["query"]
        context = scenario.get("context", {})
        
        print(f"\n--- Session: {s_id}, User Input: '{query}' ---")
        result = orchestrator.run(s_id, query, context)
        
        print(f"  Orchestrator Response Agent Type: {result['agent_type']}")
        print(f"  Orchestrator Response: {result['response']['response'][:100]}...")
        
        # Verify active agent in session store
        current_session_state = orchestrator.conversation_store.get_state(s_id)
        if current_session_state:
            print(f"  Current active agent in store: {current_session_state.get('active_agent')}")
            print(f"  Analysis in progress in store: {current_session_state.get('agent_specific_state', {}).get('analysis_in_progress')}")
        
        # Basic assertions
        assert result['agent_type'] == scenario['expected_agent'] or \
               (scenario['expected_agent'] == "riskmanaging" and result['agent_type'] == "orchestrator" and "reason" in result['response']['metadata']), \
               f"Expected agent {scenario['expected_agent']}, got {result['agent_type']}"
        
        if scenario.get("expect_report"):
            assert "analysis_id" in result['response']['response'], f"Expected report, but 'analysis_id' not found in response: {result['response']['response']}"
            print("  ✅ Report expected and received.")
        
        if scenario.get("expect_follow_up"):
            assert result['response']['metadata'].get("conversation_status", {}).get("analysis_ready") is False, "Expected follow-up, but analysis was ready."
            print("  ✅ Follow-up expected and received.")