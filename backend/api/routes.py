"""
API Routes
"""
import asyncio
import logging
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List

from backend.agents.base import BaseAgent
from backend.dependencies import get_email_agent, get_llm_gateway, get_document_retriever
from backend.agents.quiz_agent import QuizAgent, _quiz_store
from backend.agents.eval_agent import evaluate_quiz_list

router = APIRouter()
logger = logging.getLogger(__name__)

# Module-level singletons
quiz_agent = QuizAgent()
_orchestrator = None


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
    difficulty: Optional[str] = Field(default=None, description="난이도: easy, medium, hard (미지정 시 혼합 출제)")


class QuizAnswerRequest(BaseModel):
    """퀴즈 답안 제출 요청"""
    quiz_id: str
    answer: int = Field(ge=0, le=3, description="선택한 보기 인덱스 (0~3)")


class QuizEvalRequest(BaseModel):
    """퀴즈 품질 수동 평가 요청"""
    quiz_ids: List[str] = Field(..., description="평가할 퀴즈 ID 목록")


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


# ====== Helper Functions ======

def _get_orchestrator():
    """
    Lazy initialization for Orchestrator

    Returns:
        Orchestrator instance
    """
    global _orchestrator

    if _orchestrator is None:
        logger.info("Initializing Orchestrator (lazy init)...")
        from backend.agents.orchestrator import Orchestrator

        # Use existing dependency injection functions
        llm = get_llm_gateway()
        retriever = get_document_retriever()
        _orchestrator = Orchestrator(llm, retriever)
        logger.info("Orchestrator initialized successfully")

    return _orchestrator


# ====== Common Endpoints ======

@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Main chat endpoint - routes to appropriate agent based on intent

    Uses Orchestrator for multi-agent routing:
    - Intent classification
    - Agent selection (email_coach, quiz, risk_detect, ceo_sim, general_chat)
    - Response formatting

    Request example:
    {
        "message": "이메일 검토: We ship via FOB",
        "context": {}
    }
    """
    try:
        logger.info(f"Chat request: {request.message[:100]}...")

        # Get orchestrator (lazy init)
        orchestrator = _get_orchestrator()

        # Run orchestrator in thread pool to avoid blocking event loop
        result = await asyncio.to_thread(
            orchestrator.run,
            user_input=request.message,  # Map message -> user_input for compatibility
            context=request.context or {}
        )

        # Convert AgentResponse to ChatResponse
        return ChatResponse(
            response=result.response,
            agent_type=result.agent_type,
            metadata=result.metadata
        )

    except Exception as e:
        logger.error(f"Chat endpoint failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Chat processing failed: {str(e)}"
        )


# ====== Quiz Agent Endpoints ======

@router.post("/quiz/start")
async def start_quiz(request: QuizRequest):
    """퀴즈를 생성하여 반환한다. 내부에서 EvalTool 검증 + 재시도가 자동 수행된다."""
    result = await quiz_agent.run(
        "퀴즈 생성",
        {"action": "generate", "difficulty": request.difficulty},
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
    """저장된 퀴즈를 수동으로 품질 검증한다."""
    quiz_list = []
    for qid in request.quiz_ids:
        data = _quiz_store.get(qid)
        if not data:
            raise HTTPException(status_code=404, detail=f"퀴즈 ID '{qid}'를 찾을 수 없습니다.")
        quiz_list.append({**data, "quiz_id": qid})

    results = await evaluate_quiz_list(quiz_list)
    return {"results": results}


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
