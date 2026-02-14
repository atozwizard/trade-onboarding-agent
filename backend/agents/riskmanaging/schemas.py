# backend/agents/riskmanaging/schemas.py

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
import uuid

# --- Agent Inputs ---
class RiskManagingAgentInput(BaseModel):
    user_input: str = Field(..., description="사용자의 원본 질의")
    context: Optional[Dict[str, Any]] = Field(None, description="추가적인 비즈니스 맥락 정보")
    conversation_history: Optional[List[Dict[str, str]]] = Field(None, description="이전 대화 내역")

# --- Risk Engine Outputs ---
class RiskFactor(BaseModel):
    name: str = Field(..., description="평가 항목명 (예: 재정적 손실, 일정 지연)")
    impact: int = Field(..., ge=1, le=5, description="영향도 (1-5)")
    likelihood: int = Field(..., ge=1, le=5, description="발생 가능성 (1-5)")
    risk_score: int = Field(..., ge=1, le=25, description="리스크 점수 (Impact * Likelihood)")
    risk_level: str = Field(..., description="리스크 수준 (low/medium/high/critical)")
    reasoning: str = Field(..., description="해당 점수 및 수준이 나온 구체적인 근거")
    mitigation_suggestions: List[str] = Field(..., description="리스크 완화 방안 제안")

class RiskScoring(BaseModel):
    overall_risk_level: str = Field(..., description="전반적인 리스크 수준")
    risk_factors: List[RiskFactor] = Field(..., description="항목별 리스크 요인 및 평가")
    overall_assessment: str = Field(..., description="전반적인 리스크 평가 요약")

class LossSimulation(BaseModel):
    quantitative: Optional[str] = Field(None, description="정량적 손실 시뮬레이션 (예: $10,000 ~ $50,000)")
    qualitative: str = Field(..., description="정성적 손실 시뮬레이션 설명")

class ControlGapAnalysis(BaseModel):
    identified_gaps: List[str] = Field(..., description="현재 리스크 관리 체계의 허점")
    recommendations: List[str] = Field(..., description="허점 보완을 위한 제안")

class PreventionStrategy(BaseModel):
    short_term: List[str] = Field(..., description="단기 예방 전략")
    long_term: List[str] = Field(..., description="장기 예방 전략")

# --- Report Risk Factor (for frontend display) ---
class ReportRiskFactor(BaseModel):
    name_kr: str = Field(..., description="리스크 요인 한국어 이름")
    impact: int = Field(..., ge=1, le=5, description="영향도 (1-5)")
    likelihood: int = Field(..., ge=1, le=5, description="발생 가능성 (1-5)")
    score: int = Field(..., ge=1, le=25, description="리스크 점수 (Impact * Likelihood)") # 'score' to match frontend expectation


# --- Final Report Output ---
class RiskReport(BaseModel):
    analysis_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="리스크 분석 고유 ID")
    input_summary: str = Field(..., description="사용자 질의 및 컨텍스트 요약")
    risk_factors: Dict[str, ReportRiskFactor] = Field(..., description="식별된 주요 리스크 요인들을 {name: ReportRiskFactor} 형태로 요약")
    risk_scoring: RiskScoring = Field(..., description="전반적인 리스크 점수화 및 수준")
    loss_simulation: LossSimulation = Field(..., description="예상 손실 시뮬레이션")
    control_gap_analysis: ControlGapAnalysis = Field(..., description="리스크 관리 체계 허점 분석")
    prevention_strategy: PreventionStrategy = Field(..., description="예방 및 대응 전략")
    similar_cases: List[Dict[str, Any]] = Field(..., description="RAG를 통해 조회된 유사 사례")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="분석 결과에 대한 에이전트의 신뢰도 (0.0 ~ 1.0)")
    evidence_sources: List[str] = Field(..., description="분석에 활용된 근거 문서 출처")

class RiskManagingAgentResponse(BaseModel):
    response: str = Field(..., description="에이전트의 최종 응답 (JSON 문자열)")
    agent_type: str = Field("riskmanaging", description="에이전트 유형")
    metadata: Dict[str, Any] = Field(..., description="에이전트 실행 관련 추가 메타데이터")
