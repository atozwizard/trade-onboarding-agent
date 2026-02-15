"""
Orchestrator 테스트
"""
import pytest
from backend.agents.orchestrator import Orchestrator
from backend.infrastructure.upstage_llm import UpstageLLMGateway
from backend.infrastructure.chroma_retriever import ChromaDocumentRetriever
from backend.config import get_settings


@pytest.fixture
def orchestrator():
    """Orchestrator 픽스처"""
    settings = get_settings()
    llm = UpstageLLMGateway(api_key=settings.upstage_api_key)
    retriever = ChromaDocumentRetriever(settings=settings)
    return Orchestrator(llm, retriever)


class TestEmailCoachRouting:
    """Email Coach 라우팅 테스트"""

    def test_email_review_routes_to_email_agent(self, orchestrator):
        """이메일 검토 요청 → email_coach 라우팅"""
        result = orchestrator.run("이메일 검토: We ship via FOB", {})

        assert result.agent_type == "email_coach"
        assert result.response is not None
        # EmailAgent가 동작하므로 "리스크" 또는 "톤" 키워드 포함
        assert "리스크" in result.response or "톤" in result.response or "무역" in result.response

    def test_email_draft_routes_to_email_agent(self, orchestrator):
        """이메일 초안 작성 요청 → email_coach 라우팅"""
        result = orchestrator.run("바이어에게 견적 요청 이메일 작성해줘", {})

        assert result.agent_type == "email_coach"
        assert result.response is not None


class TestQuizRouting:
    """Quiz 라우팅 테스트"""

    def test_quiz_request_routes_to_quiz_stub(self, orchestrator):
        """퀴즈 요청 → quiz stub"""
        result = orchestrator.run("퀴즈 내줘", {})

        assert result.agent_type == "quiz"
        assert "준비 중" in result.response or "not_implemented" in str(result.metadata)


class TestRiskDetectRouting:
    """Risk Detection 라우팅 테스트"""

    def test_risk_detect_routes_to_stub(self, orchestrator):
        """리스크 감지 요청 → risk_detect stub"""
        result = orchestrator.run("실수할 만한 부분 알려줘", {})

        assert result.agent_type == "risk_detect"
        assert "준비 중" in result.response or "not_implemented" in str(result.metadata)


class TestGeneralChatRouting:
    """General Chat 라우팅 테스트"""

    def test_general_question_routes_to_general_chat(self, orchestrator):
        """일반 질문 → general_chat"""
        result = orchestrator.run("FOB가 뭐야?", {})

        assert result.agent_type == "general_chat"
        assert result.response is not None


class TestErrorHandling:
    """에러 핸들링 테스트"""

    def test_orchestrator_handles_llm_error_gracefully(self, orchestrator):
        """LLM 에러 시 폴백 동작 확인"""
        # 빈 입력
        result = orchestrator.run("", {})

        # 에러가 발생해도 응답 반환
        assert result.response is not None
        assert result.agent_type in ["general_chat", "out_of_scope", "email_coach"]
