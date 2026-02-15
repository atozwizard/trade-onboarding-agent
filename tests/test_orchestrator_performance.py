"""
Orchestrator 성능 테스트
"""
import pytest
import time
from backend.agents.orchestrator import Orchestrator
from backend.infrastructure.upstage_llm import UpstageLLMGateway
from backend.infrastructure.chroma_retriever import ChromaDocumentRetriever
from backend.config import get_settings


@pytest.fixture
def orchestrator():
    settings = get_settings()
    llm = UpstageLLMGateway(api_key=settings.upstage_api_key)
    retriever = ChromaDocumentRetriever(settings)
    return Orchestrator(llm, retriever)


def test_email_coach_response_time(orchestrator):
    """Email Coach 응답 시간 측정 (목표: 15초 이내)"""
    start = time.time()

    result = orchestrator.run("이메일 검토: We ship via FOB", {})

    elapsed = time.time() - start

    print(f"\n응답 시간: {elapsed:.2f}초")
    assert result.agent_type == "email_coach"
    assert elapsed < 20.0  # 20초 이내 (여유 있게)


def test_intent_classification_speed(orchestrator):
    """의도 분류 속도 측정 (목표: 3초 이내)"""
    start = time.time()

    result = orchestrator.run("퀴즈 내줘", {})

    elapsed = time.time() - start

    print(f"\n의도 분류 + 응답 시간: {elapsed:.2f}초")
    assert result.agent_type == "quiz"
    assert elapsed < 5.0  # 5초 이내


def test_multiple_requests_performance(orchestrator):
    """연속 요청 성능 측정"""
    requests = [
        "이메일 검토해줘",
        "퀴즈 내줘",
        "실수 알려줘",
    ]

    total_time = 0
    for req in requests:
        start = time.time()
        orchestrator.run(req, {})
        elapsed = time.time() - start
        total_time += elapsed

    avg_time = total_time / len(requests)
    print(f"\n평균 응답 시간: {avg_time:.2f}초")
    assert avg_time < 10.0  # 평균 10초 이내
