"""
Review Service - 이메일 검토 서비스

책임:
- 이메일 검토 총괄
- 리스크 탐지 + 톤 분석 통합
- 완전한 수정안 생성
- 응답 포맷팅
"""
import logging
from typing import Dict, List

from backend.agents.base import AgentResponse
from backend.ports import LLMGateway, DocumentRetriever
from backend.agents.email.response_formatter import ResponseFormatter
from backend.agents.email.risk_detector import RiskDetector
from backend.agents.email.tone_analyzer import ToneAnalyzer


class ReviewService:
    """이메일 검토 서비스"""

    def __init__(
        self,
        llm: LLMGateway,
        retriever: DocumentRetriever,
        improvement_prompt: str,
        risk_detector: RiskDetector,
        tone_analyzer: ToneAnalyzer
    ):
        """
        Args:
            llm: LLM Gateway
            retriever: Document Retriever
            improvement_prompt: 수정안 생성 프롬프트
            risk_detector: 리스크 탐지기
            tone_analyzer: 톤 분석기
        """
        self._llm = llm
        self._retriever = retriever
        self._improvement_prompt = improvement_prompt
        self._risk_detector = risk_detector
        self._tone_analyzer = tone_analyzer
        self._logger = logging.getLogger(__name__)
        self._formatter = ResponseFormatter()

    def review_email(self, user_input: str, context: Dict) -> AgentResponse:
        """
        Review Mode: 이메일 검토 + 리스크 탐지

        Args:
            user_input: 사용자 입력
            context: 이메일 내용, 수신자 국가 등

        Returns:
            AgentResponse
        """
        self._logger.info("Review Service activated")

        # 이메일 내용 추출
        email_content = self._extract_email_content(user_input, context)
        if not email_content:
            return self._error_response()

        # RAG 검색 - 실수 사례 + 우수 이메일
        retrieved_mistakes, retrieved_emails = self._search_references(email_content)

        # 리스크 탐지
        self._logger.info("Analyzing risks...")
        risks = self._risk_detector.detect(email_content, retrieved_mistakes, context)
        self._logger.info(f"Detected {len(risks)} risks")

        # 톤 분석
        self._logger.info("Analyzing tone...")
        tone_analysis = self._tone_analyzer.analyze(email_content, retrieved_emails, context)
        self._logger.info(f"Tone score: {tone_analysis.get('score', 0)}/10")

        # 완전한 수정안 생성
        self._logger.info("Generating complete improvement...")
        improved_email = self._generate_improvement(
            email_content,
            risks,
            tone_analysis,
            retrieved_emails
        )

        # 출처 추출
        sources = self._extract_sources(retrieved_mistakes, retrieved_emails)

        # 최종 응답 포맷팅
        response_text = self._format_response(
            email_content,
            risks,
            tone_analysis,
            improved_email,
            retrieved_mistakes,
            sources
        )

        return AgentResponse(
            response=response_text,
            agent_type="email",
            metadata={
                "mode": "review",
                "risks": risks,
                "risk_count": len(risks),
                "tone_score": tone_analysis.get('score', 0),
                "current_tone": tone_analysis.get('current_tone', 'unknown'),
                "sources": sources,
                "retrieved_mistakes": len(retrieved_mistakes),
                "retrieved_emails": len(retrieved_emails),
                "phase": 5
            }
        )

    def _extract_email_content(self, user_input: str, context: Dict) -> str:
        """이메일 내용 추출"""
        email_content = context.get("email_content", "")
        if not email_content:
            # user_input에서 추출 시도
            email_content = self._formatter.extract_email_from_input(user_input)
        return email_content

    def _error_response(self) -> AgentResponse:
        """에러 응답 생성"""
        return AgentResponse(
            response="❌ **오류**: 검토할 이메일 내용이 없습니다.\n\n`context['email_content']`에 이메일을 입력해주세요.",
            agent_type="email",
            metadata={
                "mode": "review",
                "error": "missing_email_content"
            }
        )

    def _search_references(self, email_content: str) -> tuple:
        """RAG 기반 참고 자료 검색"""
        self._logger.info("Searching for mistake cases and reference emails...")

        try:
            # 실수 사례 검색
            retrieved_mistakes = self._retriever.search(
                query=email_content,
                k=5,
                document_type="common_mistake"
            )
            self._logger.info(f"Found {len(retrieved_mistakes)} mistake cases")

            # 우수 이메일 사례도 참고용으로 검색
            retrieved_emails = self._retriever.search(
                query=email_content,
                k=2,
                document_type="email"
            )
            self._logger.info(f"Found {len(retrieved_emails)} email templates")

            return retrieved_mistakes, retrieved_emails

        except Exception as e:
            self._logger.warning(f"RAG search failed: {e}")
            return [], []

    def _generate_improvement(
        self,
        email_content: str,
        risks: List[Dict],
        tone_analysis: Dict,
        retrieved_emails: List
    ) -> str:
        """
        완전한 수정안 생성 (LLM 사용)

        Args:
            email_content: 원본 이메일
            risks: 탐지된 리스크
            tone_analysis: 톤 분석 결과
            retrieved_emails: 참고 이메일

        Returns:
            완전히 개선된 이메일
        """
        if not risks and tone_analysis.get('score', 0) >= 8:
            return email_content + "\n\n✅ 이메일이 이미 우수합니다. 수정 불필요."

        # 프롬프트 구성
        formatted_risks = self._formatter.format_risks(risks)
        formatted_emails = self._formatter.format_retrieved_docs_for_prompt(retrieved_emails)

        prompt = self._improvement_prompt.format(
            email_content=email_content,
            risks=formatted_risks,
            current_tone=tone_analysis.get('current_tone', 'unknown'),
            recommended_tone=tone_analysis.get('recommended_tone', 'professional'),
            tone_score=tone_analysis.get('score', 0),
            tone_issues=', '.join(tone_analysis.get('issues', [])[:3]),
            retrieved_emails=formatted_emails
        )

        # LLM 호출
        try:
            improved = self._llm.invoke(prompt)

            # "개선된 이메일:" 같은 접두어 제거
            if improved.startswith("개선된 이메일:"):
                improved = improved.replace("개선된 이메일:", "").strip()

            return improved

        except Exception as e:
            self._logger.warning(f"Improvement generation error: {e}")
            # 폴백: 간단한 수정안
            return self._generate_simple_improvement(email_content, risks)

    def _generate_simple_improvement(
        self,
        email_content: str,
        risks: List[Dict]
    ) -> str:
        """리스크 기반 간단한 수정안 생성 (폴백용)"""
        if not risks:
            return email_content + "\n\n✅ 발견된 리스크 없음. 현재 이메일이 적절합니다."

        # 간단한 수정안
        improvements = []
        for risk in risks:
            improvements.append(f"- {risk['recommendation']}")

        return f"""{email_content}

[개선 제안]
{chr(10).join(improvements)}"""

    def _extract_sources(self, retrieved_mistakes: List, retrieved_emails: List) -> List[str]:
        """출처 추출"""
        sources = []
        for doc in retrieved_mistakes:
            sources.append(doc.metadata.get("source_dataset", "unknown"))
        for doc in retrieved_emails:
            sources.append(doc.metadata.get("source_dataset", "unknown"))
        return sources

    def _format_response(
        self,
        email_content: str,
        risks: List[Dict],
        tone_analysis: Dict,
        improved_email: str,
        retrieved_mistakes: List,
        sources: List[str]
    ) -> str:
        """최종 응답 포맷팅"""
        formatted_mistakes = self._formatter.format_retrieved_docs(retrieved_mistakes)
        formatted_risks = self._formatter.format_risks(risks)
        formatted_improvements = self._formatter.format_improvements_with_tone(risks, tone_analysis)
        formatted_sources = self._formatter.format_sources(sources)

        return f"""### 🚨 발견된 리스크 ({len(risks)}건)

{formatted_risks}

---

### 🎨 톤 분석 결과

{tone_analysis.get('summary', 'N/A')}

**현재 톤**: {tone_analysis.get('current_tone', 'unknown')}
**권장 톤**: {tone_analysis.get('recommended_tone', 'professional')}
**톤 점수**: {tone_analysis.get('score', 0)}/10

---

### 📝 수정안

**Before**:
```
{email_content}
```

**After**:
```
{improved_email}
```

---

### 📚 개선 포인트

{formatted_improvements}

---

### 💡 참고한 실수 사례 ({len(retrieved_mistakes)}개)

{formatted_mistakes[:400]}{"..." if len(formatted_mistakes) > 400 else ""}

---

**출처**: {formatted_sources}

**✅ Phase 5 완료**: 리스크 탐지, 톤 분석, 완전한 수정안이 생성되었습니다!
"""
