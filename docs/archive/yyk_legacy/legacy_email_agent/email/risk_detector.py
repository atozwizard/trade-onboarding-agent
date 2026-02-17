"""
Risk Detector - 이메일 리스크 탐지

책임:
- LLM 기반 리스크 분석
- JSON 응답 파싱 (3단계 Fallback)
- 기본 키워드 기반 리스크 체크
"""
import logging
import json
import re
from typing import List, Dict

from backend.ports import LLMGateway
from backend.agents.email.response_formatter import ResponseFormatter


class RiskDetector:
    """이메일 리스크 탐지기"""

    def __init__(self, llm: LLMGateway, risk_prompt: str):
        """
        Args:
            llm: LLM Gateway
            risk_prompt: 리스크 탐지 프롬프트 템플릿
        """
        self._llm = llm
        self._risk_prompt = risk_prompt
        self._logger = logging.getLogger(__name__)
        self._formatter = ResponseFormatter()

    def detect(
        self,
        email_content: str,
        retrieved_mistakes: List,
        context: Dict
    ) -> List[Dict]:
        """
        이메일 내용을 분석하여 리스크 탐지

        Args:
            email_content: 검토할 이메일
            retrieved_mistakes: RAG로 검색된 실수 사례
            context: 추가 컨텍스트

        Returns:
            리스크 리스트
            [
                {
                    "type": str,
                    "severity": "critical" | "high" | "medium",
                    "current": str,
                    "risk": str,
                    "recommendation": str
                },
                ...
            ]
        """
        # 실수 사례 포맷팅
        formatted_mistakes = self._formatter.format_retrieved_docs_for_prompt(retrieved_mistakes)

        # 프롬프트 구성
        prompt = self._risk_prompt.format(
            email_content=email_content,
            retrieved_mistakes=formatted_mistakes
        )

        # LLM 호출
        try:
            response = self._llm.invoke(prompt)
            risks = self._parse_response(response)

            # 심각도 순 정렬 (critical > high > medium)
            severity_order = {"critical": 1, "high": 2, "medium": 3, "low": 4}
            risks.sort(key=lambda x: severity_order.get(x.get("severity", "low"), 99))

            return risks[:5]  # 최대 5개

        except Exception as e:
            self._logger.warning(f"Risk detection error: {e}")
            # 폴백: 기본 리스크 체크
            return self._basic_risk_check(email_content)

    def _parse_response(self, response: str) -> List[Dict]:
        """
        LLM 응답에서 리스크 리스트 파싱 (3단계 Fallback)

        Args:
            response: LLM 응답 (JSON 형식 기대)

        Returns:
            파싱된 리스크 리스트
        """
        # Tier 1: JSON 블록 추출
        json_match = re.search(r'```json\n(.*?)\n```', response, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
        else:
            # Tier 2: 전체를 JSON으로 시도
            json_str = response.strip()

        try:
            parsed = json.loads(json_str)

            # 리스트인지 확인
            if isinstance(parsed, list):
                return parsed
            elif isinstance(parsed, dict) and "risks" in parsed:
                return parsed["risks"]
            else:
                self._logger.warning("Unexpected JSON format")
                return []

        except json.JSONDecodeError as e:
            self._logger.warning(f"JSON parsing failed: {e}")
            # Tier 3: 텍스트 파싱 시도
            return self._parse_from_text(response)

    def _parse_from_text(self, text: str) -> List[Dict]:
        """
        JSON 파싱 실패 시 텍스트에서 리스크 추출

        Args:
            text: LLM 응답 텍스트

        Returns:
            추출된 리스크 리스트
        """
        risks = []

        # 간단한 패턴 매칭
        # 예: "1. [CRITICAL] missing_payment_terms"
        lines = text.split('\n')
        current_risk = {}

        for line in lines:
            # 리스크 타입 감지
            if re.match(r'\d+\.\s*\[', line):
                if current_risk:
                    risks.append(current_risk)
                current_risk = {
                    "type": "unknown",
                    "severity": "medium",
                    "current": "",
                    "risk": "파싱 실패",
                    "recommendation": "수동 확인 필요"
                }

                # severity 추출
                if 'CRITICAL' in line.upper():
                    current_risk["severity"] = "critical"
                elif 'HIGH' in line.upper():
                    current_risk["severity"] = "high"

        if current_risk:
            risks.append(current_risk)

        return risks[:3]  # 최대 3개

    def _basic_risk_check(self, email_content: str) -> List[Dict]:
        """
        기본 리스크 체크 (LLM 실패 시 폴백)

        Args:
            email_content: 이메일 내용

        Returns:
            기본 리스크 리스트
        """
        risks = []
        email_lower = email_content.lower()

        # 결제 조건 체크
        if not any(kw in email_lower for kw in ["payment", "t/t", "l/c", "deposit"]):
            risks.append({
                "type": "missing_payment_terms",
                "severity": "high",
                "current": "(결제 조건 미명시)",
                "risk": "결제 시기 불명확, 분쟁 가능성",
                "recommendation": "Payment terms: T/T 30% deposit, 70% before shipment"
            })

        # Incoterms 체크
        if not any(kw in email_lower for kw in ["fob", "cif", "exw", "ddp"]):
            risks.append({
                "type": "missing_incoterms",
                "severity": "high",
                "current": "(Incoterms 미명시)",
                "risk": "운송비 및 책임 범위 불명확",
                "recommendation": "Specify Incoterms (e.g., FOB Shanghai)"
            })

        # 공격적 톤 체크
        if any(kw in email_lower for kw in ["i need", "you must", "immediately", "urgent"]):
            risks.append({
                "type": "aggressive_tone",
                "severity": "medium",
                "current": "명령조/압박 표현 사용",
                "risk": "바이어 불쾌감, 관계 악화",
                "recommendation": "Could you please / We would appreciate 등 정중한 표현 사용"
            })

        return risks
