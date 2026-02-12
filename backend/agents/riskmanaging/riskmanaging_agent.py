import sys
import io
import os
import json
import uuid
from typing import Dict, Any, List, Optional
import openai
from openai import OpenAI
from langsmith import traceable

# Explicitly set stdout/stderr encoding to UTF-8
sys.stdout = io.TextIOWrapper(sys.stdout.detach(), encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.detach(), encoding='utf-8')

# Ensure backend directory is in path for imports
# The path manipulation needs to account for the new nested structure.
# current_dir is backend/agents/riskmanaging, need to reach backend/rag
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '..', '..', '..')) # Go up three levels to reach backend
sys.path.append(project_root)

# Local imports from the new modular structure
from backend.config import get_settings
from backend.rag.embedder import get_embedding # Needed for similarity engine if it initializes Solar internally

from backend.agents.riskmanaging.config import (
    SIMILARITY_THRESHOLD,
    RISK_AGENT_TRIGGER_WORDS, # For direct display in tests
    AGENT_PERSONA # For system prompt to LLM if needed
)
from backend.agents.riskmanaging.schemas import (
    RiskManagingAgentInput,
    RiskManagingAgentResponse,
    RiskReport
)
from backend.agents.riskmanaging.trigger_detector import detect_risk_trigger
from backend.agents.riskmanaging.similarity_engine import SimilarityEngine
from backend.agents.riskmanaging.conversation_manager import ConversationManager
from backend.agents.riskmanaging.rag_connector import RAGConnector
from backend.agents.riskmanaging.risk_engine import RiskEngine
from backend.agents.riskmanaging.report_generator import ReportGenerator
from backend.agents.riskmanaging.prompt_loader import RISK_AGENT_SYSTEM_PROMPT


class RiskManagingAgent:
    """
    Enterprise Risk Managing Agent for simulating real company risk analysis.
    Orchestrates various sub-modules for trigger detection, conversation management,
    RAG, risk evaluation, and report generation.
    """
    agent_type: str = "riskmanaging"
    
    def __init__(self):
        self.settings = get_settings()
        self.trigger_detector = detect_risk_trigger # Function directly, not a class instance
        self.similarity_engine = SimilarityEngine()
        self.conversation_manager = ConversationManager()
        self.rag_connector = RAGConnector()
        self.risk_engine = RiskEngine()
        self.report_generator = ReportGenerator()

        # Initialize LLM client for general agent persona interactions if needed outside of sub-modules
        if not self.settings.upstage_api_key:
            print("Warning: UPSTAGE_API_KEY is not set. LLM calls will fail.")
            self.llm_client = None
        else:
            self.llm_client = OpenAI(
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


    @traceable(name="riskmanaging_agent_run")
    def run(self, 
            user_input: str, 
            conversation_history: List[Dict[str, str]], 
            analysis_in_progress: bool,
            context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Runs the Enterprise Risk Managing Agent's logic.

        Args:
            user_input (str): The user's query or description of the situation.
            conversation_history (List[Dict[str, str]]): The current conversation history.
            analysis_in_progress (bool): Flag indicating if a risk analysis is currently in progress.
            context (Optional[Dict[str, Any]]): Additional context for decision-making.

        Returns:
            Dict[str, Any]: A dictionary containing the agent's response, type, metadata,
                            and the updated conversation_history and analysis_in_progress.
        """
        if context is None:
            context = {}

        # Add current user input to conversation history (for multi-turn context)
        updated_conversation_history = list(conversation_history) # Create a mutable copy
        updated_conversation_history.append({"role": "User", "content": user_input})

        updated_analysis_in_progress = analysis_in_progress

        try:
            # --- Trigger & Similarity Detection ---
            is_triggered = self.trigger_detector(user_input)
            is_similar = self.similarity_engine.check_similarity(user_input, SIMILARITY_THRESHOLD)

            if not is_triggered and not is_similar and not updated_analysis_in_progress:
                # If no trigger/similarity and no analysis is in progress, it's a passthrough
                return {
                    "response": RiskManagingAgentResponse(
                        response="General conversation: This query does not require risk analysis. (Passthrough)",
                        agent_type=self.agent_type,
                        metadata={"triggered": False, "similar": False, "reason": "Passthrough"}
                    ).model_dump(),
                    "conversation_history": updated_conversation_history,
                    "analysis_in_progress": updated_analysis_in_progress # Still False
                }

            updated_analysis_in_progress = True # Mark analysis as in progress

            # --- Conversation Management (Multi-turn) ---
            agent_input = RiskManagingAgentInput(
                user_input=user_input,
                context=context,
                conversation_history=updated_conversation_history
            )
            
            conversation_status = self.conversation_manager.assess_conversation_progress(agent_input)

            if not conversation_status.get("analysis_ready"):
                # Information is insufficient, return follow-up questions
                agent_response_message = conversation_status.get("message", "정보가 불충분합니다.")
                if conversation_status.get("follow_up_questions"):
                    agent_response_message += "\n" + "\n".join(conversation_status["follow_up_questions"])
                
                updated_conversation_history.append({"role": "Agent", "content": agent_response_message})
                
                return {
                    "response": RiskManagingAgentResponse(
                        response=agent_response_message,
                        agent_type=self.agent_type,
                        metadata={
                            "triggered": is_triggered,
                            "similar": is_similar,
                            "conversation_status": conversation_status
                        }
                    ).model_dump(),
                    "conversation_history": updated_conversation_history,
                    "analysis_in_progress": updated_analysis_in_progress
                }
            
            # If analysis_ready is True, proceed with full analysis
            # Final user query for RAG and Risk Engine is the last user input + full history
            full_context_for_analysis = agent_input.user_input # or a synthesis of history
            
            # --- RAG Connection ---
            retrieved_documents = self.rag_connector.get_risk_documents(full_context_for_analysis, updated_conversation_history)
            rag_info = self.rag_connector.extract_similar_cases_and_evidence(retrieved_documents)
            
            similar_cases = rag_info.get("similar_cases", [])
            evidence_sources = rag_info.get("evidence_sources", [])

            # --- Risk Engine ---
            risk_scoring = self.risk_engine.evaluate_risk(agent_input, retrieved_documents)

            # --- Report Generation ---
            final_report: RiskReport = self.report_generator.generate_report(
                agent_input=agent_input,
                risk_scoring=risk_scoring,
                similar_cases=similar_cases,
                evidence_sources=evidence_sources,
                rag_documents=retrieved_documents,
                context=context
            )
            
            # Reset conversation state after generating a report
            updated_conversation_history = []
            updated_analysis_in_progress = False

            return {
                "response": RiskManagingAgentResponse(
                    response=final_report.model_dump_json(indent=2, exclude_none=True), # JSON ONLY output
                    agent_type=self.agent_type,
                    metadata={
                        "triggered": is_triggered,
                        "similar": is_similar,
                        "final_report_id": final_report.analysis_id
                    }
                ).model_dump(),
                "conversation_history": updated_conversation_history,
                "analysis_in_progress": updated_analysis_in_progress
            }

        except Exception as e:
            error_message = f"리스크 관리 에이전트 실행 중 오류 발생: {e}"
            print(error_message)
            updated_conversation_history.append({"role": "Agent", "content": error_message}) # Log error in history
            updated_analysis_in_progress = False # Reset state
            return {
                "response": RiskManagingAgentResponse(
                    response=error_message,
                    agent_type=self.agent_type,
                    metadata={"error": str(e), "input": agent_input.model_dump() if 'agent_input' in locals() else user_input}
                ).model_dump(),
                "conversation_history": updated_conversation_history,
                "analysis_in_progress": updated_analysis_in_progress
            }

# The main execution block for testing the RiskManagingAgent
if __name__ == '__main__':
    # Ensure UPSTAGE_API_KEY and optionally LANGSMITH_API_KEY are set in .env for testing
    settings = get_settings()
    if not settings.upstage_api_key:
        print("UPSTAGE_API_KEY is not set in your .env file. RAG/LLM calls will be skipped.")
    if settings.langsmith_tracing and not settings.langsmith_api_key:
        print("LANGSMITH_API_KEY is not set. Langsmith tracing will be disabled.")
    
    print("--- Enterprise Risk Managing Agent Test ---")
    
    agent = RiskManagingAgent()

    test_scenarios = [
        # Scenario 1: No trigger, no similarity -> Passthrough
        {"query": "오늘 날씨 어때요?", "expected_trigger": False, "expected_similarity": False, "expected_pass_through": True},
        {"query": "파이썬에서 리스트 컴프리헨션 설명해줘", "expected_trigger": False, "expected_similarity": False, "expected_pass_through": True},

        # Scenario 2: Triggered input, but needs more info -> Multi-turn
        {"query": "신규 프로젝트 진행 중에 문제가 발생했습니다.", "expected_trigger": True, "expected_similarity": True}, # '문제' is trigger, '신규 프로젝트 문제' is similar
        {"query": "어떤 문제입니까? 구체적으로 설명해주세요.", "is_follow_up": True}, # Agent's follow up
        {"query": "납기 지연과 품질 이슈가 동시에 발생했습니다. 계약 위반 가능성도 있습니다.", "is_follow_up": True}, # User provides more info
        {"query": "관련된 계약서 내용, 지연 기간, 예상 손실액을 알려주세요.", "is_follow_up": True}, # Agent's follow up
        {"query": "A사와의 10만 달러 계약이고, 5일 이상 지연 시 일당 1% 페널티가 있습니다. 예상 손실액은 5천 달러입니다.", "is_follow_up": True, "expected_analysis": True}, # User provides enough info

        # Scenario 3: Directly enough info, triggered -> Full analysis
        {"query": "해외 거래처로부터 선적이 1주일 지연될 것 같다고 통보받았습니다. 계약서상 3일 이상 지연 시 페널티가 있습니다. 어떻게 대응해야 할까요?", "expected_trigger": True, "expected_similarity": True, "expected_analysis": True},
    ]

    print(f"\nRunning with UPSTAGE_API_KEY: {'*****' + settings.upstage_api_key[-4:] if settings.upstage_api_key else 'Not Set'}")
    print(f"Langsmith Tracing: {settings.langsmith_tracing and bool(settings.langsmith_api_key)}")

    current_test_history = []

    for i, scenario in enumerate(test_scenarios):
        query = scenario["query"]
        is_follow_up = scenario.get("is_follow_up", False)
        
        print(f"\n--- Scenario {i+1}: User Query: '{query}' ---")
        
        if not is_follow_up: # Reset history for new main scenarios
            agent.conversation_history = []
            agent.analysis_in_progress = False

        result = agent.run(query, {})
        
        print(f"Agent Response (type: {result['agent_type']}):")
        if isinstance(result['response'], str) and result['response'].startswith('{'):
            try:
                # Pretty print JSON responses
                print(json.dumps(json.loads(result['response']), indent=2, ensure_ascii=False))
            except json.JSONDecodeError:
                print(result['response']) # Print raw if not valid JSON
        else:
            print(result['response'])
        
        if result['metadata'].get("conversation_status", {}).get("analysis_ready"):
            print(">>> Analysis was ready and report should have been generated.")
        
        if result['metadata'].get("triggered") is not None:
            print(f"  Metadata: Triggered={result['metadata'].get('triggered')}, Similar={result['metadata'].get('similar')}")
