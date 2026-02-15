"""
Response Formatter - 응답 포맷팅 유틸리티

책임:
- RAG 검색 결과 포맷팅 (프롬프트용/사용자 응답용)
- 리스크 마크다운 포맷팅
- 개선안 포맷팅
- 출처 포맷팅
- 이메일 추출
"""
import re
from typing import List, Dict


class ResponseFormatter:
    """응답 포맷팅 유틸리티 클래스"""

    @staticmethod
    def format_risks(risks: List[Dict]) -> str:
        """
        리스크 리스트를 마크다운으로 포맷

        Args:
            risks: 리스크 리스트

        Returns:
            포맷된 문자열
        """
        if not risks:
            return "✅ 발견된 리스크 없음! 이메일이 안전합니다."

        formatted = []
        severity_icon = {
            "critical": "🔴",
            "high": "🟠",
            "medium": "🟡",
            "low": "🟢"
        }

        for i, risk in enumerate(risks, 1):
            icon = severity_icon.get(risk.get("severity", "medium"), "⚪")
            severity = risk.get("severity", "medium").upper()
            risk_type = risk.get("type", "unknown")
            current = risk.get("current", "N/A")
            risk_desc = risk.get("risk", "N/A")
            recommendation = risk.get("recommendation", "N/A")

            formatted.append(f"""**{i}. [{icon} {severity}] {risk_type}**
- 현재: "{current}"
- 리스크: {risk_desc}
- 권장: {recommendation}
""")

        return "\n".join(formatted)

    @staticmethod
    def format_improvements(risks: List[Dict]) -> str:
        """
        개선 포인트 요약

        Args:
            risks: 리스크 리스트

        Returns:
            개선 포인트 문자열
        """
        if not risks:
            return "✅ 개선 필요 사항 없음"

        improvements = []
        for i, risk in enumerate(risks[:3], 1):  # 상위 3개만
            risk_type = risk.get("type", "unknown").replace("_", " ").title()
            recommendation = risk.get("recommendation", "N/A")
            improvements.append(f"{i}. **{risk_type}**: {recommendation}")

        return "\n".join(improvements)

    @staticmethod
    def format_improvements_with_tone(
        risks: List[Dict],
        tone_analysis: Dict
    ) -> str:
        """
        리스크 + 톤 분석 기반 개선 포인트 요약

        Args:
            risks: 리스크 리스트
            tone_analysis: 톤 분석 결과

        Returns:
            개선 포인트 문자열
        """
        improvements = []

        # 리스크 기반 개선점 (상위 3개)
        for i, risk in enumerate(risks[:3], 1):
            risk_type = risk.get("type", "unknown").replace("_", " ").title()
            improvements.append(f"{i}. ✅ **{risk_type}**: {risk.get('recommendation', 'N/A')[:80]}...")

        # 톤 개선점
        if tone_analysis.get('score', 10) < 8:
            tone_improvements = tone_analysis.get('improvements', [])
            for improvement in tone_improvements[:2]:  # 최대 2개
                improvements.append(f"{len(improvements)+1}. 🎨 **톤 개선**: {improvement[:80]}...")

        return "\n".join(improvements) if improvements else "✅ 개선 필요 사항 없음"

    @staticmethod
    def format_retrieved_docs_for_prompt(docs: List) -> str:
        """
        RAG 검색 결과를 LLM 프롬프트용으로 포맷

        Args:
            docs: retriever 검색 결과 (RetrievedDocument 객체 리스트)

        Returns:
            프롬프트에 주입할 문자열
        """
        if not docs:
            return "관련 이메일 샘플을 찾지 못했습니다. 일반적인 비즈니스 이메일 형식으로 작성하세요."

        formatted = []
        for i, doc in enumerate(docs, 1):
            content = doc.content
            metadata = doc.metadata

            formatted.append(f"""[샘플 {i}]
내용: {content}
상황: {metadata.get('situation', 'N/A')}
출처: {metadata.get('source_dataset', 'unknown')}
""")

        return "\n".join(formatted)

    @staticmethod
    def format_retrieved_docs(docs: List) -> str:
        """
        RAG 검색 결과를 읽기 쉬운 형식으로 포맷

        Args:
            docs: retriever.search() 결과 (RetrievedDocument 객체 리스트)

        Returns:
            포맷된 문자열 (마크다운)
        """
        if not docs:
            return "❌ 관련 문서를 찾지 못했습니다."

        formatted = []
        for i, doc in enumerate(docs, 1):
            content = doc.content
            metadata = doc.metadata
            distance = doc.distance

            # 신뢰도 표시 (distance가 낮을수록 유사도 높음)
            if distance < 0.5:
                confidence = "🟢 [높은 유사도]"
            elif distance < 1.0:
                confidence = "🟡 [중간 유사도]"
            else:
                confidence = "⚪ [낮은 유사도]"

            # 출처
            source = metadata.get("source_dataset", "unknown")

            # 포맷팅
            formatted.append(f"""**{i}. {confidence}** (거리: {distance:.2f})
- 내용: {content[:100]}{"..." if len(content) > 100 else ""}
- 출처: {source}
""")

        return "\n".join(formatted)

    @staticmethod
    def format_sources(sources: List[str]) -> str:
        """
        출처 목록을 문자열로 포맷

        Args:
            sources: 출처 ID 리스트 (예: ["emails.json", "mistakes.json"])

        Returns:
            포맷된 문자열 (예: "emails.json, mistakes.json")
        """
        if not sources:
            return "N/A"

        # 중복 제거
        unique_sources = list(set(sources))

        return ", ".join(unique_sources[:3])  # 최대 3개만 표시

    @staticmethod
    def extract_email_from_input(user_input: str) -> str:
        """
        user_input에서 이메일 본문 추출

        간단한 휴리스틱:
        - ":" 이후 텍스트를 이메일로 간주
        - 여러 줄인 경우 전체 추출

        Args:
            user_input: 사용자 입력

        Returns:
            추출된 이메일 내용 (없으면 빈 문자열)
        """
        if ":" in user_input:
            # "검토해줘: Hi, ..." 형식
            parts = user_input.split(":", 1)
            if len(parts) > 1:
                return parts[1].strip()

        return ""
