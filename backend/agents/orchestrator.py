"""
Orchestrator - Multi-Agent 라우터

책임:
- LangGraph Workflow 정의
- 의도 분류 → 조건부 라우팅 → 에이전트 실행 → 응답 포맷팅
- 기존 EmailAgent 래핑 (수정 없음)
"""

import logging
from typing import Dict, Any

from langgraph.graph import StateGraph, END

from backend.agents.agent_state import AgentState
from backend.agents.intent_classifier import IntentClassifier
from backend.agents.email.email_agent import EmailCoachAgent
from backend.ports import LLMGateway, DocumentRetriever
from backend.agents.base import AgentResponse


class Orchestrator:
    """Multi-Agent Orchestrator (LangGraph 기반)"""

    def __init__(self, llm: LLMGateway, retriever: DocumentRetriever):
        """
        Args:
            llm: LLM Gateway
            retriever: Document Retriever
        """
        self._llm = llm
        self._retriever = retriever
        self._logger = logging.getLogger(__name__)

        # 서브 컴포넌트
        self._classifier = IntentClassifier(llm)
        self._email_agent = EmailCoachAgent(llm, retriever)  # 기존 EmailAgent 그대로

        # LangGraph Workflow 빌드
        self._workflow = self._build_workflow()

    def _build_workflow(self) -> StateGraph:
        """LangGraph Workflow 구성"""
        workflow = StateGraph(AgentState)

        # 노드 추가
        workflow.add_node("classify_intent", self._classify_intent_node)
        workflow.add_node("email_agent", self._email_agent_node)
        workflow.add_node("quiz_agent", self._quiz_stub_node)
        workflow.add_node("risk_detect", self._risk_detect_stub_node)
        workflow.add_node("general_chat", self._general_chat_node)
        workflow.add_node("format_response", self._format_response_node)

        # 조건부 라우팅 (5-way)
        workflow.add_conditional_edges(
            "classify_intent",
            self._route_by_intent,
            {
                "email_coach": "email_agent",
                "quiz": "quiz_agent",
                "risk_detect": "risk_detect",
                "general_chat": "general_chat",
                "out_of_scope": "general_chat",
            }
        )

        # 각 에이전트 → format_response
        for agent_node in ["email_agent", "quiz_agent", "risk_detect", "general_chat"]:
            workflow.add_edge(agent_node, "format_response")

        # 최종 종료
        workflow.add_edge("format_response", END)

        # 시작점 설정
        workflow.set_entry_point("classify_intent")

        return workflow.compile()

    def run(self, user_input: str, context: Dict[str, Any]) -> AgentResponse:
        """
        Orchestrator 실행

        Args:
            user_input: 사용자 입력
            context: 세션 컨텍스트

        Returns:
            AgentResponse
        """
        # 초기 State
        initial_state: AgentState = {
            "user_input": user_input,
            "intent": "general_chat",  # 기본값
            "context": context,
            "response": "",
            "metadata": {},
            "error": None
        }

        # Workflow 실행
        try:
            final_state = self._workflow.invoke(initial_state)

            return AgentResponse(
                response=final_state["response"],
                agent_type=final_state["intent"],
                metadata=final_state["metadata"]
            )
        except Exception as e:
            self._logger.error(f"Orchestrator error: {e}")
            return AgentResponse(
                response="시스템 오류가 발생했습니다. 다시 시도해주세요.",
                agent_type="error",
                metadata={"error": str(e)}
            )

    # ============================================================
    # Nodes
    # ============================================================

    def _classify_intent_node(self, state: AgentState) -> AgentState:
        """Step 1: 의도 분류"""
        try:
            intent = self._classifier.classify(state["user_input"], state["context"])
            state["intent"] = intent
        except Exception as e:
            self._logger.error(f"Intent classification error: {e}")
            state["error"] = f"Intent classification error: {e}"
            state["intent"] = "general_chat"  # 폴백
        return state

    def _route_by_intent(self, state: AgentState) -> str:
        """조건부 라우팅 로직"""
        return state["intent"]

    def _email_agent_node(self, state: AgentState) -> AgentState:
        """Email Agent 노드 (기존 EmailAgent 래핑)"""
        try:
            # 기존 EmailAgent.run() 그대로 호출
            result = self._email_agent.run(state["user_input"], state["context"])
            state["response"] = result.response
            state["metadata"] = result.metadata
        except Exception as e:
            self._logger.error(f"Email agent error: {e}")
            state["error"] = f"Email agent error: {e}"
            state["response"] = "이메일 검토 중 오류가 발생했습니다. 다시 시도해주세요."
            state["metadata"] = {"error": True}
        return state

    def _quiz_stub_node(self, state: AgentState) -> AgentState:
        """Quiz Agent 준비 (미구현)"""
        state["response"] = "📝 **퀴즈 기능 준비 중**\n\n무역 용어 학습 퀴즈 기능은 곧 제공됩니다."
        state["metadata"] = {"agent_type": "quiz", "status": "not_implemented"}
        return state

    def _risk_detect_stub_node(self, state: AgentState) -> AgentState:
        """Risk Detection Agent 준비 (미구현)"""
        state["response"] = "⚠️ **리스크 감지 기능 준비 중**\n\n업무 상황별 예상 실수 감지 기능은 곧 제공됩니다."
        state["metadata"] = {"agent_type": "risk_detect", "status": "not_implemented"}
        return state

    def _general_chat_node(self, state: AgentState) -> AgentState:
        """일반 질문 응답 (간단한 폴백)"""
        state["response"] = "무역 관련 질문에 답변드립니다. 더 구체적인 질문을 해주세요.\n\n예시:\n- 이메일 검토해줘\n- 퀴즈 내줘\n- 실수할 만한 부분 알려줘"
        state["metadata"] = {"agent_type": "general_chat"}
        return state

    def _format_response_node(self, state: AgentState) -> AgentState:
        """공통 응답 포맷팅"""
        # 에러가 있으면 에러 메시지 추가 (개발 모드)
        if state.get("error"):
            state["response"] += f"\n\n_Debug: {state['error']}_"
        return state
