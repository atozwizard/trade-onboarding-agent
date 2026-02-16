"""
Tone Analyzer - 이메일 톤 분석

책임:
- LLM 기반 톤 분석
- 문화권별 톤 적합성 평가
- JSON 응답 파싱
"""
import logging
import json
import re
from typing import List, Dict

from backend.ports import LLMGateway
from backend.agents.email.response_formatter import ResponseFormatter


class ToneAnalyzer:
    """이메일 톤 분석기"""

    def __init__(self, llm: LLMGateway, tone_prompt: str):
        """
        Args:
            llm: LLM Gateway
            tone_prompt: 톤 분석 프롬프트 템플릿
        """
        self._llm = llm
        self._tone_prompt = tone_prompt
        self._logger = logging.getLogger(__name__)
        self._formatter = ResponseFormatter()

    def analyze(
        self,
        email_content: str,
        retrieved_emails: List,
        context: Dict
    ) -> Dict:
        """
        이메일 톤 분석

        Args:
            email_content: 이메일 내용
            retrieved_emails: 참고 이메일
            context: 추가 컨텍스트 (수신자 국가 등)

        Returns:
            {
                "current_tone": str,
                "recommended_tone": str,
                "score": float,
                "summary": str,
                "issues": List[str],
                "improvements": List[str]
            }
        """
        recipient_country = context.get("recipient_country", "")
        formatted_emails = self._formatter.format_retrieved_docs_for_prompt(retrieved_emails)

        # 프롬프트 구성
        prompt = self._tone_prompt.format(
            email_content=email_content,
            recipient_country=recipient_country or "N/A (assume global professional standard)",
            relationship=context.get("relationship", "unknown"),
            purpose=context.get("purpose", "unknown"),
            retrieved_emails=formatted_emails
        )

        # LLM 호출
        try:
            response = self._llm.invoke(prompt)
            tone_result = self._parse_response(response)
            return tone_result

        except Exception as e:
            self._logger.warning(f"Tone analysis error: {e}")
            # 폴백: 기본 톤 분석
            return {
                "current_tone": "unknown",
                "recommended_tone": "professional",
                "score": 5.0,
                "summary": f"톤 분석 중 오류 발생: {str(e)}",
                "issues": [],
                "improvements": []
            }

    def _parse_response(self, response: str) -> Dict:
        """
        LLM 톤 분석 응답 파싱

        Args:
            response: LLM 응답 (JSON 형식 기대)

        Returns:
            파싱된 톤 분석 결과
        """
        # JSON 블록 추출
        json_match = re.search(r'```json\n(.*?)\n```', response, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
        else:
            json_str = response.strip()

        try:
            parsed = json.loads(json_str)
            # 기본값 설정
            return {
                "current_tone": parsed.get("current_tone", "unknown"),
                "recommended_tone": parsed.get("recommended_tone", "professional"),
                "score": float(parsed.get("score", 5.0)),
                "summary": parsed.get("summary", "톤 분석 완료"),
                "issues": parsed.get("issues", []),
                "improvements": parsed.get("improvements", []),
                "cultural_notes": parsed.get("cultural_notes", [])
            }

        except (json.JSONDecodeError, ValueError) as e:
            self._logger.warning(f"Tone JSON parsing failed: {e}")
            # 폴백: 텍스트에서 추출
            return {
                "current_tone": "unknown",
                "recommended_tone": "professional",
                "score": 5.0,
                "summary": response[:200],
                "issues": [],
                "improvements": []
            }
