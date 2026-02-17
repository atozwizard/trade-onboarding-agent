"""
Email Coach Agent - Facade (Phase 3 리팩토링 완료)

기능:
- Draft Mode: 이메일 초안 작성
- Review Mode: 이메일 검토 + 리스크 탐지 + 톤 분석

Phase 3 리팩토링:
- God Class (997줄) → 7개 서비스로 분해
- 단일 책임 원칙 준수
- 테스트 가능성 향상
"""
import logging
from typing import Dict, Literal

from backend.agents.base import BaseAgent, AgentResponse
from backend.ports import LLMGateway, DocumentRetriever
from backend.prompts.email_prompt import load_all_prompts

# 모듈화된 서비스들
from backend.agents.email.draft_service import DraftService
from backend.agents.email.review_service import ReviewService
from backend.agents.email.risk_detector import RiskDetector
from backend.agents.email.tone_analyzer import ToneAnalyzer


class EmailCoachAgent(BaseAgent):
    """
    이메일 코칭 에이전트 (Facade)

    Phase 3 리팩토링:
    - 997줄 → ~150줄 (Facade만)
    - 각 기능을 전담 서비스에 위임
    - 의존성 주입 기반
    """

    def __init__(self, llm: LLMGateway, retriever: DocumentRetriever):
        """
        에이전트 초기화

        Args:
            llm: LLM Gateway (Upstage Solar 등)
            retriever: Document Retriever (ChromaDB 등)
        """
        self._llm = llm
        self._retriever = retriever
        self.prompts = load_all_prompts()
        self._logger = logging.getLogger(__name__)

        # 서비스 인스턴스 생성 (의존성 주입)
        self._risk_detector = RiskDetector(
            llm=llm,
            risk_prompt=self.prompts["risk"]
        )

        self._tone_analyzer = ToneAnalyzer(
            llm=llm,
            tone_prompt=self.prompts["tone"]
        )

        self._draft_service = DraftService(
            llm=llm,
            retriever=retriever,
            draft_prompt=self.prompts["draft"]
        )

        self._review_service = ReviewService(
            llm=llm,
            retriever=retriever,
            improvement_prompt=self.prompts["improvement"],
            risk_detector=self._risk_detector,
            tone_analyzer=self._tone_analyzer
        )

        self._logger.info("Email Coach Agent initialized (Phase 3 - Modular)")

    def run(self, user_input: str, context: Dict) -> AgentResponse:
        """
        BaseAgent 인터페이스 구현

        Args:
            user_input: 사용자 입력
                - Draft: "미국 바이어에게 견적 요청 이메일 작성해줘"
                - Review: "다음 이메일 검토해줘: Hi, ..."

            context: 추가 컨텍스트
                {
                    "mode": "draft" | "review" (선택, 자동 감지 가능),
                    "email_content": str (Review 모드 시 필요),
                    "situation": str (Draft 모드, 선택),
                    "recipient_country": str (선택),
                    "relationship": str (선택),
                    "purpose": str (Review 모드, 선택)
                }

        Returns:
            AgentResponse with:
                - response: str (마크다운 형식 응답)
                - agent_type: "email"
                - metadata: {
                    "mode": "draft" | "review",
                    "risks": List[Dict],      # Review 모드일 경우
                    "tone_score": float,      # Review 모드일 경우
                    "sources": List[str]      # RAG 검색 결과 출처
                }
        """
        self._logger.info(f"Email Coach Agent Running with input: {user_input[:50]}...")
        self._logger.debug(f"Context: {context}")

        # 1. 모드 자동 감지
        mode = self._detect_mode(user_input, context)
        self._logger.info(f"Detected mode: {mode}")

        # 2. 모드별 라우팅 (서비스에 위임)
        if mode == "draft":
            return self._draft_service.generate_draft(user_input, context)
        else:
            return self._review_service.review_email(user_input, context)

    def _detect_mode(
        self,
        user_input: str,
        context: Dict
    ) -> Literal["draft", "review"]:
        """
        사용자 입력에서 모드 자동 감지

        Rules:
        1. context["mode"] 명시 시 우선 사용
        2. "검토", "확인", "리스크", "review", "check" → review
        3. "작성", "초안", "만들어", "draft", "write" → draft
        4. context["email_content"] 존재 → review
        5. Default: draft

        Args:
            user_input: 사용자 입력
            context: 컨텍스트

        Returns:
            "draft" | "review"
        """
        # Rule 1: 명시적 모드
        if "mode" in context:
            return context["mode"]

        # Rule 2: Review 키워드
        review_keywords = ["검토", "확인", "리스크", "체크", "review", "check"]
        user_input_lower = user_input.lower()

        if any(kw in user_input_lower for kw in review_keywords):
            return "review"

        # Rule 3: Draft 키워드
        draft_keywords = ["작성", "초안", "만들어", "draft", "write"]
        if any(kw in user_input_lower for kw in draft_keywords):
            return "draft"

        # Rule 4: email_content 존재
        if "email_content" in context and context["email_content"]:
            return "review"

        # Rule 5: Default
        return "draft"
