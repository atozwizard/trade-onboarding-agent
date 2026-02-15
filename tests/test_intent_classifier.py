"""
Intent Classifier 테스트
"""
import pytest
from backend.agents.intent_classifier import IntentClassifier
from backend.infrastructure.upstage_llm import UpstageLLMGateway
from backend.config import get_settings


@pytest.fixture
def classifier():
    """IntentClassifier 픽스처"""
    settings = get_settings()
    llm = UpstageLLMGateway(api_key=settings.upstage_api_key)
    return IntentClassifier(llm)


class TestEmailCoachIntent:
    """Email Coach 의도 테스트"""

    def test_email_review_korean(self, classifier):
        result = classifier.classify("이메일 검토해줘", {})
        assert result == "email_coach"

    def test_email_draft_korean(self, classifier):
        result = classifier.classify("메일 초안 작성", {})
        assert result == "email_coach"

    def test_email_review_english(self, classifier):
        result = classifier.classify("review my email", {})
        assert result == "email_coach"


class TestQuizIntent:
    """Quiz 의도 테스트"""

    def test_quiz_request_korean(self, classifier):
        result = classifier.classify("퀴즈 내줘", {})
        assert result == "quiz"

    def test_quiz_problem_korean(self, classifier):
        result = classifier.classify("문제 풀어볼래", {})
        assert result == "quiz"


class TestRiskDetectIntent:
    """Risk Detection 의도 테스트"""

    def test_mistake_request_korean(self, classifier):
        result = classifier.classify("실수할 만한 부분 알려줘", {})
        assert result == "risk_detect"

    def test_caution_request_korean(self, classifier):
        result = classifier.classify("주의할 점은?", {})
        assert result == "risk_detect"


class TestGeneralChatIntent:
    """General Chat 의도 테스트"""

    def test_trade_term_question(self, classifier):
        result = classifier.classify("FOB가 뭐야?", {})
        assert result == "general_chat"

    def test_incoterms_question(self, classifier):
        result = classifier.classify("인코텀즈 종류 알려줘", {})
        assert result == "general_chat"


class TestOutOfScopeIntent:
    """Out of Scope 의도 테스트"""

    def test_weather_question(self, classifier):
        result = classifier.classify("날씨 어때?", {})
        assert result == "out_of_scope"

    def test_food_question(self, classifier):
        result = classifier.classify("점심 뭐 먹지?", {})
        assert result == "out_of_scope"
