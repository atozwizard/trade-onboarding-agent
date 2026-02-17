# backend/services/quiz_service.py

import uuid
import json
from datetime import datetime
from typing import List, Dict, Any, Optional

from backend.schemas.quiz import QuizQuestion
from backend.agents.orchestrator.session_store import create_conversation_store


class QuizSessionStore:
    """
    Store for quiz sessions.
    Uses the same Redis/InMemory infrastructure as conversation sessions.
    """

    def __init__(self):
        # Reuse the same store infrastructure (Redis or InMemory)
        self._store = create_conversation_store()

    def _make_key(self, session_id: str) -> str:
        """Create quiz session key with namespace"""
        return f"quiz_session:{session_id}"

    def create_session(
        self,
        questions: List[QuizQuestion],
        topic: Optional[str] = None,
        difficulty: Optional[str] = None
    ) -> str:
        """
        Create a new quiz session.

        Returns:
            session_id: Unique session ID
        """
        session_id = str(uuid.uuid4())

        session_data = {
            "quiz_session_id": session_id,
            "questions": [q.model_dump() for q in questions],
            "topic": topic,
            "difficulty": difficulty,
            "created_at": datetime.utcnow().isoformat(),
            "answers": {},  # {quiz_id: user_answer}
            "completed": False
        }

        # For Redis, this will use "session:quiz_session:{id}" key
        # For InMemory, it just stores in dict
        self._store.save_state(self._make_key(session_id), session_data)

        return session_id

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve quiz session data"""
        return self._store.get_state(self._make_key(session_id))

    def save_answer(self, session_id: str, quiz_id: str, answer: int):
        """Save user answer for a question"""
        session = self.get_session(session_id)
        if not session:
            raise ValueError(f"Quiz session {session_id} not found")

        session["answers"][quiz_id] = answer
        self._store.save_state(self._make_key(session_id), session)

    def get_question(self, session_id: str, quiz_id: str) -> Optional[QuizQuestion]:
        """Get a specific question from session"""
        session = self.get_session(session_id)
        if not session:
            return None

        for q_data in session["questions"]:
            if q_data["quiz_id"] == quiz_id:
                return QuizQuestion(**q_data)

        return None

    def mark_completed(self, session_id: str):
        """Mark quiz session as completed"""
        session = self.get_session(session_id)
        if session:
            session["completed"] = True
            self._store.save_state(self._make_key(session_id), session)


class QuizGeneratorService:
    """
    Service for generating quiz questions.
    Currently uses hardcoded sample quizzes.
    TODO: Integrate with QuizAgent for dynamic generation.
    """

    @staticmethod
    def generate_sample_quizzes(
        count: int = 5,
        topic: Optional[str] = None,
        difficulty: Optional[str] = None
    ) -> List[QuizQuestion]:
        """
        Generate sample quiz questions.

        Args:
            count: Number of questions to generate
            topic: Topic filter (not implemented yet)
            difficulty: Difficulty level (not implemented yet)

        Returns:
            List of QuizQuestion objects
        """
        # Sample quiz questions about trade terminology
        sample_questions = [
            QuizQuestion(
                quiz_id=str(uuid.uuid4()),
                question="FOB(Free On Board)의 의미는 무엇인가요?",
                choices=[
                    "본선 인도 조건 - 수출자가 물품을 본선에 적재할 때까지 책임",
                    "운임 포함 조건 - 목적지까지 운임 포함",
                    "보험료 포함 조건 - 보험료까지 포함한 가격",
                    "공장 인도 조건 - 공장에서 물품 인도"
                ],
                correct_answer=0,
                explanation="FOB(Free On Board)는 본선 인도 조건으로, 수출자가 지정 선적항에서 물품을 본선에 적재할 때까지의 비용과 위험을 부담합니다.",
                quiz_type="term_to_description",
                difficulty="easy",
                term="FOB"
            ),
            QuizQuestion(
                quiz_id=str(uuid.uuid4()),
                question="L/C(신용장)의 주요 목적은 무엇인가요?",
                choices=[
                    "수출입 거래의 대금 결제를 은행이 보증",
                    "상품의 품질을 검사",
                    "관세를 납부하는 문서",
                    "운송 계약서"
                ],
                correct_answer=0,
                explanation="L/C(Letter of Credit, 신용장)는 은행이 수입자를 대신하여 대금 지급을 보증하는 문서로, 무역 거래의 안전성을 높입니다.",
                quiz_type="term_to_description",
                difficulty="easy",
                term="L/C"
            ),
            QuizQuestion(
                quiz_id=str(uuid.uuid4()),
                question="CIF 조건에 포함되지 않는 것은?",
                choices=[
                    "통관 수수료",
                    "운임",
                    "보험료",
                    "본선 적재 비용"
                ],
                correct_answer=0,
                explanation="CIF(Cost, Insurance and Freight)는 운임과 보험료를 포함한 조건이지만, 목적지 통관 수수료는 수입자가 부담합니다.",
                quiz_type="concept_application",
                difficulty="medium",
                term="CIF"
            ),
            QuizQuestion(
                quiz_id=str(uuid.uuid4()),
                question="다음 중 Incoterms 2020에서 수출자의 책임이 가장 큰 조건은?",
                choices=[
                    "DDP (Delivered Duty Paid)",
                    "EXW (Ex Works)",
                    "FOB (Free On Board)",
                    "CFR (Cost and Freight)"
                ],
                correct_answer=0,
                explanation="DDP는 수입국 지정 장소까지 관세 납부를 포함한 모든 비용과 위험을 수출자가 부담하는 조건으로, 수출자의 책임이 가장 큽니다.",
                quiz_type="comparison",
                difficulty="hard",
                term="DDP"
            ),
            QuizQuestion(
                quiz_id=str(uuid.uuid4()),
                question="B/L(Bill of Lading)의 3대 기능이 아닌 것은?",
                choices=[
                    "보험 증서",
                    "화물 수령증",
                    "운송 계약서",
                    "권리 증권(유가증권)"
                ],
                correct_answer=0,
                explanation="B/L(선하증권)의 3대 기능은 ①화물 수령증 ②운송 계약서 ③권리 증권(유가증권)입니다. 보험 증서는 B/L의 기능이 아닙니다.",
                quiz_type="concept_knowledge",
                difficulty="medium",
                term="B/L"
            ),
            QuizQuestion(
                quiz_id=str(uuid.uuid4()),
                question="수출입 통관 시 필요한 HS Code의 자릿수는?",
                choices=[
                    "10자리 (한국 기준)",
                    "6자리 (국제 표준)",
                    "8자리",
                    "4자리"
                ],
                correct_answer=0,
                explanation="HS Code는 국제적으로 6자리를 사용하지만, 한국은 10자리를 사용합니다. 앞 6자리는 국제 공통, 뒤 4자리는 국가별로 세분화됩니다.",
                quiz_type="factual_knowledge",
                difficulty="hard",
                term="HS Code"
            ),
            QuizQuestion(
                quiz_id=str(uuid.uuid4()),
                question="다음 중 수입 신용장 개설 은행은?",
                choices=[
                    "개설 은행 (Issuing Bank)",
                    "매입 은행 (Negotiating Bank)",
                    "통지 은행 (Advising Bank)",
                    "확인 은행 (Confirming Bank)"
                ],
                correct_answer=0,
                explanation="개설 은행(Issuing Bank)은 수입자의 요청으로 신용장을 발행하는 은행입니다. 일반적으로 수입자의 거래 은행이 개설 은행이 됩니다.",
                quiz_type="term_identification",
                difficulty="easy",
                term="Issuing Bank"
            ),
        ]

        # Select questions based on count
        if count > len(sample_questions):
            count = len(sample_questions)

        return sample_questions[:count]


# Global instance
quiz_session_store = QuizSessionStore()
quiz_generator = QuizGeneratorService()
