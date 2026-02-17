"""
Trade Term Validator - 무역 용어 검증

책임:
- 이메일 내 무역 용어 추출
- RAG 기반 용어 정확성 검증
- 잘못된 용어 감지 및 올바른 용어 제안
"""

import logging
import re
from typing import List, Dict, Any

from backend.ports import LLMGateway, DocumentRetriever


class TradeTermValidator:
    """무역 용어 검증 서비스"""

    def __init__(self, llm: LLMGateway, retriever: DocumentRetriever):
        """
        Args:
            llm: LLM Gateway
            retriever: Document Retriever (RAG)
        """
        self._llm = llm
        self._retriever = retriever
        self._logger = logging.getLogger(__name__)

        # 알려진 인코텀즈 및 무역 용어
        self._known_terms = [
            # Incoterms 2020
            "EXW", "FCA", "CPT", "CIP", "DAP", "DPU", "DDP",
            "FAS", "FOB", "CFR", "CIF",
            # 결제 조건
            "L/C", "T/T", "D/P", "D/A", "O/A", "CAD",
            # 서류
            "B/L", "AWB", "C/I", "P/L", "C/O",
            # 단위
            "MT", "CBM", "CFT", "TEU", "FCL", "LCL"
        ]

    def validate(self, email_content: str) -> Dict[str, Any]:
        """
        이메일 내 무역 용어 검증

        Args:
            email_content: 이메일 본문

        Returns:
            {
                "incorrect_terms": [
                    {
                        "found": "FOV",
                        "should_be": "FOB",
                        "confidence": 0.95,
                        "context": "We will ship via FOV",
                        "definition": "Free On Board - 본선 인도 조건"
                    }
                ],
                "verified_terms": [
                    {"term": "CIF", "full_name": "Cost Insurance and Freight"}
                ],
                "suggestions": [
                    "FOV → FOB 수정 권장"
                ]
            }
        """
        try:
            # 1. 무역 용어 추출
            extracted_terms = self._extract_terms(email_content)

            if not extracted_terms:
                return {
                    "incorrect_terms": [],
                    "verified_terms": [],
                    "suggestions": []
                }

            # 2. 각 용어 검증
            incorrect_terms = []
            verified_terms = []

            for term in extracted_terms:
                # 대소문자 무시하고 검증
                term_upper = term.upper()

                # 알려진 용어와 정확히 일치하는지 확인
                if term_upper in self._known_terms:
                    # RAG로 정의 가져오기
                    definition = self._get_term_definition(term_upper)
                    verified_terms.append({
                        "term": term_upper,
                        "full_name": definition.get("full_name", ""),
                        "korean_name": definition.get("korean_name", "")
                    })
                    continue

                # 유사한 용어 검색 (RAG)
                similar_terms = self._find_similar_terms(term)

                if similar_terms:
                    best_match = similar_terms[0]
                    best_term = best_match.get("term", "").upper()
                    distance = best_match.get("distance", 1.0)

                    # 유사도 기반 판단 (distance가 낮을수록 유사)
                    # 알려진 용어와 문자열이 다르면 오타 가능성으로 처리
                    if best_term and term_upper != best_term and distance < 0.8:
                        incorrect_terms.append({
                            "found": term,
                            "should_be": best_term,
                            "confidence": 1 - distance,
                            "context": self._extract_context(email_content, term),
                            "definition": best_match.get("definition", "")
                        })
                    elif distance < 0.3:
                        # 동일 용어이거나 사실상 일치
                        verified_terms.append({
                            "term": term,
                            "full_name": best_match.get("full_name", "")
                        })

            # 3. 제안 생성
            suggestions = [
                f"{item['found']} → {item['should_be']} 수정 권장 (정확도: {item['confidence']:.0%})"
                for item in incorrect_terms
            ]

            return {
                "incorrect_terms": incorrect_terms,
                "verified_terms": verified_terms,
                "suggestions": suggestions
            }

        except Exception as e:
            self._logger.error(f"Trade term validation error: {e}")
            return {
                "incorrect_terms": [],
                "verified_terms": [],
                "suggestions": []
            }

    def _extract_terms(self, email_content: str) -> List[str]:
        """
        LLM으로 무역 용어 추출

        Args:
            email_content: 이메일 본문

        Returns:
            추출된 무역 용어 리스트
        """
        prompt = f"""다음 이메일에서 무역 용어(Incoterms, 결제 조건, 서류명, 단위 등)를 추출하세요.

이메일:
{email_content}

무역 용어만 추출하여 콤마로 구분된 리스트로 반환하세요.
예: FOB, CIF, L/C, B/L

무역 용어:"""

        try:
            response = self._llm.invoke(prompt, temperature=0.0)

            # 응답 파싱
            terms = [term.strip() for term in response.split(",") if term.strip()]

            # 정규식으로 추가 추출 (보완)
            # 대문자 약어 패턴 (2-4글자)
            pattern = r'\b([A-Z]{2,4}(?:/[A-Z])?)\b'
            regex_terms = re.findall(pattern, email_content)

            # 중복 제거하여 병합
            all_terms = list(set(terms + regex_terms))

            return all_terms[:20]  # 최대 20개

        except Exception as e:
            self._logger.warning(f"Term extraction error: {e}")
            # 폴백: 정규식만 사용
            pattern = r'\b([A-Z]{2,4}(?:/[A-Z])?)\b'
            return list(set(re.findall(pattern, email_content)))[:20]

    def _find_similar_terms(self, term: str) -> List[Dict]:
        """
        RAG로 유사한 무역 용어 검색

        Args:
            term: 검색할 용어

        Returns:
            유사한 용어 리스트 (distance 포함)
        """
        try:
            # DocumentRetriever의 search 메서드 사용
            results = self._retriever.search(
                query=term,
                k=3,
                document_type="trade_terminology"
            )

            similar_terms = []
            for doc in results:
                content, metadata, distance = self._extract_document_fields(doc)
                similar_terms.append({
                    "term": metadata.get("term", ""),
                    "full_name": metadata.get("full_name", ""),
                    "korean_name": metadata.get("korean_name", ""),
                    "definition": content.split("|")[-1].strip() if "|" in content else "",
                    "distance": distance
                })

            similar_terms.sort(key=lambda item: item.get("distance", 1.0))
            return similar_terms

        except Exception as e:
            self._logger.warning(f"RAG search error: {e}")
            return []

    def _get_term_definition(self, term: str) -> Dict:
        """
        RAG로 용어 정의 가져오기

        Args:
            term: 무역 용어

        Returns:
            용어 정의
        """
        try:
            results = self._retriever.search(
                query=term,
                k=1,
                document_type="trade_terminology"
            )

            if results:
                content, metadata, _ = self._extract_document_fields(results[0])
                return {
                    "full_name": metadata.get("full_name", ""),
                    "korean_name": metadata.get("korean_name", ""),
                    "definition": content.split("|")[-1].strip() if "|" in content else ""
                }

        except Exception as e:
            self._logger.warning(f"Definition retrieval error: {e}")

        return {}

    @staticmethod
    def _extract_document_fields(doc: Any) -> tuple[str, Dict[str, Any], float]:
        """
        RetrievedDocument(객체)와 dict 형태를 모두 지원하여 필드 추출.
        """
        if hasattr(doc, "content") and hasattr(doc, "metadata"):
            content = getattr(doc, "content", "") or ""
            metadata = getattr(doc, "metadata", {}) or {}
            distance = getattr(doc, "distance", 1.0)
            return content, metadata, float(distance if distance is not None else 1.0)

        if isinstance(doc, dict):
            content = doc.get("content", "") or doc.get("document", "")
            metadata = doc.get("metadata", {}) or {}
            distance = doc.get("distance", 1.0)
            return content, metadata, float(distance if distance is not None else 1.0)

        return "", {}, 1.0

    def _extract_context(self, email_content: str, term: str) -> str:
        """
        용어가 사용된 문맥 추출 (앞뒤 5단어)

        Args:
            email_content: 이메일 본문
            term: 용어

        Returns:
            문맥 문자열
        """
        words = email_content.split()

        try:
            # 대소문자 무시하고 찾기
            idx = next(i for i, word in enumerate(words) if term.lower() in word.lower())
            start = max(0, idx - 5)
            end = min(len(words), idx + 6)
            return " ".join(words[start:end])
        except StopIteration:
            return f"...{term}..."
