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
from backend.agents.email.trade_term_validator import TradeTermValidator
from backend.agents.email.unit_validator import UnitValidator


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
        self._term_validator = TradeTermValidator(llm, retriever)  # 신규
        self._unit_validator = UnitValidator()  # 신규
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

        # 무역 용어 검증 (신규)
        self._logger.info("Validating trade terms...")
        term_validation = self._term_validator.validate(email_content)
        self._logger.info(f"Found {len(term_validation.get('incorrect_terms', []))} incorrect terms")

        # 단위 검증 (신규)
        self._logger.info("Validating units...")
        unit_validation = self._unit_validator.validate(email_content)
        self._logger.info(f"Found {len(unit_validation.get('inconsistencies', []))} unit inconsistencies")

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
            sources,
            term_validation,  # 신규
            unit_validation   # 신규
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
                "term_validation": term_validation,  # 신규
                "unit_validation": unit_validation,  # 신규
                "phase": 6  # Phase 5 -> 6으로 변경 (신규 기능 추가)
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
        sources: List[str],
        term_validation: Dict,
        unit_validation: Dict
    ) -> str:
        """최종 응답 포맷팅"""
        formatted_mistakes = self._formatter.format_retrieved_docs(retrieved_mistakes)
        formatted_risks = self._formatter.format_risks(risks)
        formatted_improvements = self._formatter.format_improvements_with_tone(risks, tone_analysis)
        formatted_sources = self._formatter.format_sources(sources)

        # 무역 용어 검증 포맷팅
        term_section = self._format_term_validation(term_validation)

        # 단위 검증 포맷팅
        unit_section = self._format_unit_validation(unit_validation)

        return f"""### 🚨 발견된 리스크 ({len(risks)}건)

{formatted_risks}

---

### 🎨 톤 분석 결과

{tone_analysis.get('summary', 'N/A')}

**현재 톤**: {tone_analysis.get('current_tone', 'unknown')}
**권장 톤**: {tone_analysis.get('recommended_tone', 'professional')}
**톤 점수**: {tone_analysis.get('score', 0)}/10

---

{term_section}

{unit_section}

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

**✅ Phase 6 완료**: 리스크 탐지, 톤 분석, 무역 용어 검증, 단위 검증, 완전한 수정안이 생성되었습니다!
"""

    def _format_term_validation(self, term_validation: Dict) -> str:
        """무역 용어 검증 결과 포맷팅"""
        incorrect_terms = term_validation.get('incorrect_terms', [])
        verified_terms = term_validation.get('verified_terms', [])

        if not incorrect_terms and not verified_terms:
            return ""

        sections = []

        if incorrect_terms:
            sections.append("### 🔍 무역 용어 검증")
            sections.append("\n**❌ 오류 발견:**\n")
            for item in incorrect_terms:
                sections.append(f"- **{item['found']}** → **{item['should_be']}** (정확도: {item['confidence']:.0%})")
                sections.append(f"  - 문맥: `{item['context']}`")
                sections.append(f"  - 설명: {item['definition'][:100]}...")
                sections.append("")

        if verified_terms:
            sections.append("\n**✅ 올바른 용어:**")
            for item in verified_terms[:5]:  # 최대 5개
                korean = f" ({item.get('korean_name', '')})" if item.get('korean_name') else ""
                sections.append(f"- **{item['term']}**: {item.get('full_name', '')}{korean}")

        sections.append("\n---\n")
        return "\n".join(sections)

    def _format_unit_validation(self, unit_validation: Dict) -> str:
        """단위 검증 결과 포맷팅"""
        inconsistencies = unit_validation.get('inconsistencies', [])
        standardized = unit_validation.get('standardized', '')
        unit_summary = unit_validation.get('unit_summary', {})

        if not inconsistencies and not standardized:
            return ""

        sections = []
        sections.append("### 📏 단위 검증")

        if inconsistencies:
            sections.append("\n**⚠️ 불일치 발견:**\n")
            for item in inconsistencies:
                severity_icon = {
                    "critical": "🔴",
                    "high": "🟠",
                    "medium": "🟡",
                    "low": "🟢"
                }.get(item.get('severity', 'low'), "⚠️")

                sections.append(f"{severity_icon} **{item['issue']}**")
                sections.append(f"  - 발견: `{item['text']}`")
                sections.append(f"  - 제안: {item['suggestion']}")
                sections.append("")

        if standardized:
            sections.append(f"\n**✅ 표준화 제안:** `{standardized}`\n")

        # 단위 요약
        if any(unit_summary.values()):
            sections.append("\n**📊 단위 요약:**")
            if unit_summary.get('weight'):
                sections.append(f"- 무게: {', '.join(unit_summary['weight'][:3])}")
            if unit_summary.get('volume'):
                sections.append(f"- 부피: {', '.join(unit_summary['volume'][:3])}")
            if unit_summary.get('container'):
                sections.append(f"- 컨테이너: {', '.join(unit_summary['container'][:3])}")

        sections.append("\n---\n")
        return "\n".join(sections)
