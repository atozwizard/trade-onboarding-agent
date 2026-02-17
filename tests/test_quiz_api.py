# tests/test_quiz_api.py

import pytest
from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


class TestQuizAPI:
    """Test cases for Quiz API endpoints"""

    def test_start_quiz_default(self):
        """Test starting a quiz with default parameters"""
        response = client.post(
            "/api/quiz/start",
            json={}
        )

        assert response.status_code == 200
        data = response.json()

        # Check response structure
        assert "quiz_session_id" in data
        assert "questions" in data
        assert "total_questions" in data
        assert "created_at" in data

        # Check default count
        assert data["total_questions"] == 5
        assert len(data["questions"]) == 5

        # Check question structure (should not contain answers)
        first_question = data["questions"][0]
        assert "quiz_id" in first_question
        assert "question" in first_question
        assert "choices" in first_question
        assert "quiz_type" in first_question
        assert "difficulty" in first_question
        assert "correct_answer" not in first_question  # Hidden
        assert "explanation" not in first_question  # Hidden

        # Check choices
        assert len(first_question["choices"]) == 4

    def test_start_quiz_custom_count(self):
        """Test starting a quiz with custom question count"""
        response = client.post(
            "/api/quiz/start",
            json={"count": 3}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total_questions"] == 3
        assert len(data["questions"]) == 3

    def test_start_quiz_with_topic_and_difficulty(self):
        """Test starting a quiz with topic and difficulty"""
        response = client.post(
            "/api/quiz/start",
            json={
                "topic": "Incoterms",
                "difficulty": "hard",
                "count": 2
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["topic"] == "Incoterms"
        assert data["difficulty"] == "hard"
        assert data["total_questions"] == 2

    def test_answer_quiz_correct(self):
        """Test submitting a correct answer"""
        # First, start a quiz
        start_response = client.post(
            "/api/quiz/start",
            json={"count": 1}
        )
        start_data = start_response.json()
        quiz_session_id = start_data["quiz_session_id"]
        quiz_id = start_data["questions"][0]["quiz_id"]

        # Get the correct answer by checking the choices
        # For FOB question, correct answer is index 0
        response = client.post(
            "/api/quiz/answer",
            json={
                "quiz_session_id": quiz_session_id,
                "quiz_id": quiz_id,
                "answer": 0
            }
        )

        assert response.status_code == 200
        data = response.json()

        # Check response structure
        assert "quiz_id" in data
        assert "is_correct" in data
        assert "user_answer" in data
        assert "correct_answer" in data
        assert "explanation" in data
        assert "question" in data
        assert "choices" in data

        # Check answer evaluation
        assert data["quiz_id"] == quiz_id
        assert data["user_answer"] == 0
        assert isinstance(data["is_correct"], bool)
        assert len(data["explanation"]) > 0

    def test_answer_quiz_incorrect(self):
        """Test submitting an incorrect answer"""
        # Start a quiz
        start_response = client.post(
            "/api/quiz/start",
            json={"count": 1}
        )
        start_data = start_response.json()
        quiz_session_id = start_data["quiz_session_id"]
        quiz_id = start_data["questions"][0]["quiz_id"]

        # Submit wrong answer (assuming 3 is wrong for FOB question)
        response = client.post(
            "/api/quiz/answer",
            json={
                "quiz_session_id": quiz_session_id,
                "quiz_id": quiz_id,
                "answer": 3
            }
        )

        assert response.status_code == 200
        data = response.json()

        assert data["user_answer"] == 3
        # For FOB question, correct answer is 0
        if data["correct_answer"] != 3:
            assert data["is_correct"] is False

    def test_answer_quiz_invalid_session(self):
        """Test submitting answer with invalid session ID"""
        response = client.post(
            "/api/quiz/answer",
            json={
                "quiz_session_id": "invalid-session-id",
                "quiz_id": "some-quiz-id",
                "answer": 0
            }
        )

        assert response.status_code == 404

    def test_answer_quiz_invalid_question(self):
        """Test submitting answer with invalid question ID"""
        # Start a valid quiz
        start_response = client.post(
            "/api/quiz/start",
            json={"count": 1}
        )
        quiz_session_id = start_response.json()["quiz_session_id"]

        # Try to answer non-existent question
        response = client.post(
            "/api/quiz/answer",
            json={
                "quiz_session_id": quiz_session_id,
                "quiz_id": "invalid-quiz-id",
                "answer": 0
            }
        )

        assert response.status_code == 404

    def test_full_quiz_workflow(self):
        """Test complete quiz workflow: start -> answer all -> check"""
        # 1. Start quiz with 3 questions
        start_response = client.post(
            "/api/quiz/start",
            json={"count": 3}
        )
        assert start_response.status_code == 200
        start_data = start_response.json()

        quiz_session_id = start_data["quiz_session_id"]
        questions = start_data["questions"]
        assert len(questions) == 3

        # 2. Answer all questions
        results = []
        for i, question in enumerate(questions):
            answer_response = client.post(
                "/api/quiz/answer",
                json={
                    "quiz_session_id": quiz_session_id,
                    "quiz_id": question["quiz_id"],
                    "answer": i % 4  # Cycle through answers
                }
            )
            assert answer_response.status_code == 200
            results.append(answer_response.json())

        # 3. Verify all answers were recorded
        assert len(results) == 3
        for result in results:
            assert "is_correct" in result
            assert "explanation" in result


if __name__ == "__main__":
    # Quick manual test
    print("Testing Quiz API...")

    print("\n1. Starting quiz...")
    start_resp = client.post("/api/quiz/start", json={"count": 2})
    print(f"   Status: {start_resp.status_code}")
    start_data = start_resp.json()
    print(f"   Session ID: {start_data['quiz_session_id']}")
    print(f"   Questions: {start_data['total_questions']}")

    print("\n2. Answering first question...")
    quiz_id = start_data["questions"][0]["quiz_id"]
    answer_resp = client.post(
        "/api/quiz/answer",
        json={
            "quiz_session_id": start_data["quiz_session_id"],
            "quiz_id": quiz_id,
            "answer": 0
        }
    )
    print(f"   Status: {answer_resp.status_code}")
    answer_data = answer_resp.json()
    print(f"   Correct: {answer_data['is_correct']}")
    print(f"   Explanation: {answer_data['explanation'][:80]}...")

    print("\n✅ Quiz API test passed!")
