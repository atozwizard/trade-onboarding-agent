"""
API Routes
"""
import asyncio
import logging
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List

from backend.agents.base import BaseAgent
from backend.dependencies import get_email_agent
from backend.agents.quiz_agent import QuizAgent, _quiz_store
from backend.agents.eval_agent import EvalAgent

router = APIRouter()
logger = logging.getLogger(__name__)

# 모듈 레벨 싱글톤
quiz_agent = QuizAgent()
eval_agent = EvalAgent()


class ChatRequest(BaseModel):
    """Chat request model"""
    message: str
    context: Optional[Dict[str, Any]] = None


class ChatResponse(BaseModel):
    """Chat response model"""
    response: str
    agent_type: str
    metadata: Optional[Dict[str, Any]] = None


# ====== Quiz Agent Models ======

class QuizRequest(BaseModel):
    """퀴즈 생성 요청"""
    topic: str = Field(default="general", description="주제: general, mistakes, negotiation, country, documents")
    difficulty: Optional[str] = Field(default=None, description="난이도: easy, medium, hard (미지정 시 혼합 출제)")


class QuizAnswerRequest(BaseModel):
    """퀴즈 답안 제출 요청"""
    quiz_id: str
    answer: int = Field(ge=0, le=3, description="선택한 보기 인덱스 (0~3)")


class QuizEvalRequest(BaseModel):
    """퀴즈 품질 평가 요청"""
    quiz_id: str
    topic: str = Field(default="general", description="주제 (원본 데이터 대조용)")


# ====== Email Agent Models ======

class EmailDraftRequest(BaseModel):
    """Email draft generation request"""
    user_input: str = Field(..., description="사용자 요청 (예: '미국 바이어에게 견적 요청 이메일 작성')")
    recipient_country: Optional[str] = Field(None, description="수신자 국가 (예: USA, Japan, Korea)")
    relationship: Optional[str] = Field("first_contact", description="관계 (first_contact/ongoing/long_term)")
    purpose: Optional[str] = Field(None, description="이메일 목적 (quotation/negotiation/inquiry 등)")


class EmailReviewRequest(BaseModel):
    """Email review request"""
    email_content: str = Field(..., description="검토할 이메일 본문")
    recipient_country: Optional[str] = Field(None, description="수신자 국가")
    purpose: Optional[str] = Field(None, description="이메일 목적")


class RiskItem(BaseModel):
    """Individual risk item"""
    type: str
    severity: str
    location: str
    current: str
    risk: str
    recommendation: str
    source: Optional[str] = None


class ToneAnalysis(BaseModel):
    """Tone analysis result"""
    current_tone: str
    recommended_tone: str
    score: float
    issues: List[str]
    improvements: List[str]
    cultural_notes: List[str]
    summary: str


class EmailResponse(BaseModel):
    """Email agent response"""
    response: str
    agent_type: str = "email"
    metadata: Dict[str, Any]


# ====== Common Endpoints ======

@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Main chat endpoint - routes to appropriate agent based on intent
    """
    # TODO: Implement orchestrator logic
    return ChatResponse(
        response="서버가 정상 작동 중입니다. 오케스트레이터를 구현해주세요.",
        agent_type="system",
        metadata={"status": "not_implemented"}
    )


# ====== Quiz Agent Endpoints ======

@router.post("/quiz/start")
async def start_quiz(request: QuizRequest):
    """퀴즈를 생성하여 반환한다."""
    result = await quiz_agent.run(
        "퀴즈 생성",
        {"action": "generate", "topic": request.topic, "difficulty": request.difficulty},
    )

    if isinstance(result["response"], dict) and "error" in result["response"]:
        raise HTTPException(status_code=500, detail=result["response"]["error"])

    return result


@router.post("/quiz/answer")
async def answer_quiz(request: QuizAnswerRequest):
    """퀴즈 답안을 채점하고 해설을 반환한다."""
    result = await quiz_agent.run(
        "답변 제출",
        {"action": "evaluate", "quiz_id": request.quiz_id, "user_answer": request.answer},
    )

    if isinstance(result["response"], dict) and "error" in result["response"]:
        raise HTTPException(status_code=404, detail=result["response"]["error"])

    return result


@router.post("/quiz/evaluate")
async def eval_quiz(request: QuizEvalRequest):
    """생성된 퀴즈의 품질을 평가하여 검증 리포트를 반환한다."""
    quiz_data = _quiz_store.get(request.quiz_id)

    if not quiz_data:
        raise HTTPException(status_code=404, detail=f"퀴즈 ID '{request.quiz_id}'를 찾을 수 없습니다.")

    result = await eval_agent.run(
        "퀴즈 평가",
        {"quiz_data": quiz_data, "topic": request.topic},
    )

    if isinstance(result["response"], dict) and "error" in result["response"]:
        raise HTTPException(status_code=500, detail=result["response"]["error"])

    return result


# ====== Email Agent Endpoints ======

@router.post("/email/draft", response_model=EmailResponse)
async def draft_email(
    request: EmailDraftRequest,
    agent: BaseAgent = Depends(get_email_agent)
):
    """
    Generate email draft with RAG + LLM
    """
    try:
        logger.info(f"Draft email request: {request.user_input[:50]}...")

        context = {
            "mode": "draft",
            "recipient_country": request.recipient_country or "Unknown",
            "relationship": request.relationship,
            "purpose": request.purpose
        }

        result = await asyncio.to_thread(
            agent.run,
            user_input=request.user_input,
            context=context
        )

        return EmailResponse(**result.to_dict())

    except Exception as e:
        logger.error(f"Draft email failed: {e}")
        raise HTTPException(status_code=500, detail=f"Email draft generation failed: {str(e)}")


@router.post("/email/review", response_model=EmailResponse)
async def review_email(
    request: EmailReviewRequest,
    agent: BaseAgent = Depends(get_email_agent)
):
    """
    Review existing email for risks, tone, and improvements
    """
    try:
        logger.info(f"Review email request: {len(request.email_content)} characters")

        context = {
            "mode": "review",
            "email_content": request.email_content,
            "recipient_country": request.recipient_country or "Unknown",
            "purpose": request.purpose
        }

        result = await asyncio.to_thread(
            agent.run,
            user_input="",
            context=context
        )

        return EmailResponse(**result.to_dict())

    except Exception as e:
        logger.error(f"Review email failed: {e}")
        raise HTTPException(status_code=500, detail=f"Email review failed: {str(e)}")
