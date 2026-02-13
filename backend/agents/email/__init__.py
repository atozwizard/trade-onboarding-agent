"""
Email Coach Agent - Modular Services

Phase 3 리팩토링: God Class를 7개 서비스로 분리

Services:
    - EmailCoachAgent: Facade (진입점)
    - DraftService: 이메일 초안 생성
    - ReviewService: 이메일 검토 총괄
    - RiskDetector: 리스크 탐지
    - ToneAnalyzer: 톤 분석
    - ChecklistGenerator: 5W1H 체크리스트
    - ResponseFormatter: 응답 포맷팅
"""
from backend.agents.email.email_agent import EmailCoachAgent

__all__ = ["EmailCoachAgent"]
