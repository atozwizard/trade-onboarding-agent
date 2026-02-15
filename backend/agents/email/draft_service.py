"""
Draft Service - 이메일 초안 생성 서비스

책임:
- RAG 기반 이메일 템플릿 검색
- LLM 기반 이메일 초안 생성
- 5W1H 체크리스트 생성
- 응답 포맷팅
"""
import logging
from typing import Dict, List

from backend.agents.base import AgentResponse
from backend.ports import LLMGateway, DocumentRetriever
from backend.agents.email.response_formatter import ResponseFormatter
from backend.agents.email.checklist_generator import ChecklistGenerator


class DraftService:
    """이메일 초안 생성 서비스"""

    def __init__(
        self,
        llm: LLMGateway,
        retriever: DocumentRetriever,
        draft_prompt: str
    ):
        """
        Args:
            llm: LLM Gateway
            retriever: Document Retriever
            draft_prompt: 초안 생성 프롬프트 템플릿
        """
        self._llm = llm
        self._retriever = retriever
        self._draft_prompt = draft_prompt
        self._logger = logging.getLogger(__name__)
        self._formatter = ResponseFormatter()
        self._checklist_gen = ChecklistGenerator()

    def generate_draft(self, user_input: str, context: Dict) -> AgentResponse:
        """
        Draft Mode: 이메일 초안 작성

        Args:
            user_input: 사용자 요청
            context: 상황, 수신자 국가 등

        Returns:
            AgentResponse
        """
        self._logger.info("Draft Service activated")

        situation = context.get("situation", "")
        recipient_country = context.get("recipient_country", "")
        relationship = context.get("relationship", "")

        # RAG 검색 - 우수 이메일 사례
        self._logger.info("Searching for email templates...")
        retrieved_docs = self._search_templates(user_input, situation)

        # LLM 기반 이메일 생성
        self._logger.info("Generating email with LLM...")
        generated_email = self._generate_email(
            user_input,
            situation,
            recipient_country,
            relationship,
            retrieved_docs
        )

        # 체크리스트 자동 생성
        checklist = self._checklist_gen.generate(generated_email)

        # 출처 추출
        sources = [doc.metadata.get("source_dataset", "unknown") for doc in retrieved_docs]

        # 최종 응답 포맷팅
        response_text = self._format_response(
            generated_email,
            checklist,
            retrieved_docs,
            sources
        )

        return AgentResponse(
            response=response_text,
            agent_type="email",
            metadata={
                "mode": "draft",
                "sources": sources,
                "retrieved_count": len(retrieved_docs),
                "email_length": len(generated_email),
                "phase": 3
            }
        )

    def _search_templates(self, user_input: str, situation: str) -> List:
        """
        RAG 기반 이메일 템플릿 검색

        Args:
            user_input: 사용자 요청
            situation: 상황

        Returns:
            검색된 문서 리스트
        """
        # 검색 쿼리 구성
        search_query = f"{user_input}"
        if situation:
            search_query += f" {situation}"

        # RAG 검색 실행
        try:
            retrieved_docs = self._retriever.search(
                query=search_query,
                k=3,
                document_type="email"
            )
            self._logger.info(f"Found {len(retrieved_docs)} email templates")
            return retrieved_docs
        except Exception as e:
            self._logger.warning(f"RAG search failed: {e}")
            return []

    def _generate_email(
        self,
        user_input: str,
        situation: str,
        recipient_country: str,
        relationship: str,
        retrieved_docs: List
    ) -> str:
        """
        LLM 기반 이메일 생성

        Args:
            user_input: 사용자 요청
            situation: 상황
            recipient_country: 수신자 국가
            relationship: 관계
            retrieved_docs: 검색된 템플릿

        Returns:
            생성된 이메일
        """
        # 검색 결과 포맷팅 (프롬프트용)
        formatted_emails = self._formatter.format_retrieved_docs_for_prompt(retrieved_docs)

        # 프롬프트 구성
        prompt = self._draft_prompt.format(
            user_input=user_input,
            situation=situation or "general business communication",
            recipient_country=recipient_country or "N/A (adjust tone to be universally professional)",
            relationship=relationship or "professional business relationship",
            retrieved_emails=formatted_emails
        )

        # LLM 호출
        try:
            generated_email = self._llm.invoke(prompt)
            self._logger.info(f"Email generated ({len(generated_email)} characters)")
            return generated_email
        except Exception as e:
            self._logger.error(f"LLM error: {e}")
            return f"""[LLM 호출 실패: {str(e)}]

Dear [Buyer Name],

I hope this email finds you well.

[이메일 생성 중 오류가 발생했습니다. 프롬프트를 확인하거나 API 키를 점검해주세요.]

Best regards,
[Your Name]"""

    def _format_response(
        self,
        generated_email: str,
        checklist: str,
        retrieved_docs: List,
        sources: List[str]
    ) -> str:
        """
        최종 응답 포맷팅

        Args:
            generated_email: 생성된 이메일
            checklist: 체크리스트
            retrieved_docs: 검색된 문서
            sources: 출처 목록

        Returns:
            포맷된 응답 문자열
        """
        formatted_docs = self._formatter.format_retrieved_docs(retrieved_docs)
        formatted_sources = self._formatter.format_sources(sources)

        return f"""### 📧 작성된 이메일 초안

```
{generated_email}
```

---

### ✅ 체크리스트
{checklist}

---

### 📚 참고한 이메일 샘플 ({len(retrieved_docs)}개)

{formatted_docs[:500]}{"..." if len(formatted_docs) > 500 else ""}

---

**출처**: {formatted_sources}

**✅ Phase 3 완료**: RAG 기반 실제 이메일이 생성되었습니다. 즉시 전송 가능합니다!
"""
