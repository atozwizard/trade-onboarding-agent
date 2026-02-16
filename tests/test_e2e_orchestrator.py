"""
End-to-End Orchestrator 테스트
"""
import pytest
import requests
import time


BASE_URL = "http://localhost:8000"


@pytest.fixture(scope="module")
def wait_for_server():
    """서버 시작 대기"""
    max_retries = 10
    for i in range(max_retries):
        try:
            response = requests.get(f"{BASE_URL}/health")
            if response.status_code == 200:
                return
        except requests.exceptions.ConnectionError:
            if i < max_retries - 1:
                time.sleep(1)
            else:
                raise


class TestE2EEmailCoach:
    """Email Coach E2E 테스트"""

    def test_email_review_request(self, wait_for_server):
        """이메일 검토 요청 E2E"""
        response = requests.post(
            f"{BASE_URL}/api/chat",
            json={
                "message": "이메일 검토: We will ship the goods via FOB incoterms.",
                "context": {}
            }
        )

        assert response.status_code == 200
        data = response.json()

        assert data["agent_type"] == "email_coach"
        assert "response" in data
        assert len(data["response"]) > 0

    def test_email_draft_request(self, wait_for_server):
        """이메일 초안 작성 요청 E2E"""
        response = requests.post(
            f"{BASE_URL}/api/chat",
            json={
                "message": "바이어에게 견적 요청 이메일 작성해줘",
                "context": {}
            }
        )

        assert response.status_code == 200
        data = response.json()

        assert data["agent_type"] == "email_coach"


class TestE2EQuiz:
    """Quiz E2E 테스트"""

    def test_quiz_request(self, wait_for_server):
        """퀴즈 요청 E2E"""
        response = requests.post(
            f"{BASE_URL}/api/chat",
            json={
                "message": "퀴즈 내줘",
                "context": {}
            }
        )

        assert response.status_code == 200
        data = response.json()

        assert data["agent_type"] == "quiz"
        assert "준비 중" in data["response"]


class TestE2ERiskDetect:
    """Risk Detection E2E 테스트"""

    def test_risk_detect_request(self, wait_for_server):
        """리스크 감지 요청 E2E"""
        response = requests.post(
            f"{BASE_URL}/api/chat",
            json={
                "message": "실수할 만한 부분 알려줘",
                "context": {}
            }
        )

        assert response.status_code == 200
        data = response.json()

        assert data["agent_type"] == "risk_detect"
        assert "준비 중" in data["response"]


class TestE2EGeneralChat:
    """General Chat E2E 테스트"""

    def test_general_question(self, wait_for_server):
        """일반 질문 E2E"""
        response = requests.post(
            f"{BASE_URL}/api/chat",
            json={
                "message": "FOB가 뭐야?",
                "context": {}
            }
        )

        assert response.status_code == 200
        data = response.json()

        assert data["agent_type"] == "general_chat"
