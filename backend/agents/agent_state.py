"""
Agent State - LangGraph 상태 정의

책임:
- Orchestrator Workflow의 상태 정의
- 타입 힌팅 제공
"""

from typing import TypedDict, Literal, Optional, Dict, Any


class AgentState(TypedDict):
    """
    Orchestrator State

    Attributes:
        user_input: 사용자 원본 입력
        intent: 분류된 의도 (5가지)
        context: 세션 컨텍스트 (이전 대화 등)
        response: 최종 응답 텍스트
        metadata: 에이전트별 메타데이터 (점수, 리스크 등)
        error: 에러 메시지 (있을 경우)
    """
    user_input: str
    intent: Literal["quiz", "email_coach", "risk_detect", "general_chat", "out_of_scope"]
    context: Dict[str, Any]
    response: str
    metadata: Dict[str, Any]
    error: Optional[str]
