"""
Base Agent Interface

모든 에이전트가 구현해야 하는 추상 클래스와 공통 데이터 구조
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Any, Optional


@dataclass
class AgentResponse:
    """
    에이전트 응답 표준 구조

    Attributes:
        response: 사용자에게 표시할 응답 메시지 (마크다운 형식)
        agent_type: 에이전트 타입 ("quiz", "email", "mistake", "ceo")
        metadata: 추가 정보 (점수, 검색 결과, 통계 등)
    """
    response: str
    agent_type: str
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """API 응답용 딕셔너리 변환"""
        return {
            "response": self.response,
            "agent_type": self.agent_type,
            "metadata": self.metadata or {}
        }


class BaseAgent(ABC):
    """
    에이전트 기본 인터페이스

    모든 에이전트(Quiz, Email, Mistake, CEO)는 이 추상 클래스를 상속해야 합니다.
    Orchestrator는 BaseAgent 타입으로 모든 에이전트를 다룰 수 있습니다.

    Example:
        class EmailCoachAgent(BaseAgent):
            def run(self, user_input: str, context: Dict[str, Any]) -> AgentResponse:
                # 구현
                return AgentResponse(
                    response="...",
                    agent_type="email",
                    metadata={...}
                )
    """

    @abstractmethod
    def run(self, user_input: str, context: Dict[str, Any]) -> AgentResponse:
        """
        에이전트 실행 (메인 엔트리포인트)

        Args:
            user_input: 사용자 입력 메시지
            context: 컨텍스트 정보 (mode, email_content 등)

        Returns:
            AgentResponse: 구조화된 응답 객체

        Raises:
            ValueError: 입력이 유효하지 않을 때
            RuntimeError: 에이전트 실행 중 복구 불가능한 오류 발생 시
        """
        pass

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}>"
