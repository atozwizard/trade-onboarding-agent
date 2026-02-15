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

router = APIRouter()
logger = logging.getLogger(__name__)

# Global Orchestrator instance (lazy initialization)
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


@router.post("/quiz/start")
async def start_quiz(topic: str = "general", difficulty: str = "easy"):
    """
    Start a new quiz session
    """
    # TODO: Implement quiz generation
    return {
        "message": "퀴즈 생성 기능을 구현해주세요.",
        "topic": topic,
        "difficulty": difficulty
    }


@router.post("/quiz/answer")
async def answer_quiz(quiz_id: str, answer: int):
    """
    Submit quiz answer and get feedback
    """
    # TODO: Implement quiz evaluation
    return {
        "message": "퀴즈 채점 기능을 구현해주세요.",
        "quiz_id": quiz_id,
        "answer": answer
    }


# ====== Email Agent Endpoints ======

@router.post("/email/draft", response_model=EmailResponse)
async def draft_email(
    request: EmailDraftRequest,
    agent: BaseAgent = Depends(get_email_agent)
):
    """
    Generate email draft with RAG + LLM

    Request example:
    {
        "user_input": "미국 바이어에게 FOB 조건으로 100개 견적 요청",
        "recipient_country": "USA",
        "relationship": "first_contact",
        "purpose": "quotation"
    }
    """
    try:
        logger.info(f"Draft email request: {request.user_input[:50]}...")

        context = {
            "mode": "draft",
            "recipient_country": request.recipient_country or "Unknown",
            "relationship": request.relationship,
            "purpose": request.purpose
        }

        # Run agent in thread pool to avoid blocking event loop
        result = await asyncio.to_thread(
            agent.run,
            user_input=request.user_input,
            context=context
        )

        # Convert AgentResponse to dict for EmailResponse
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

    Request example:
    {
        "email_content": "Hi, send me 100 units quickly. We'll pay later.",
        "recipient_country": "Japan",
        "purpose": "quotation"
    }
    """
    try:
        logger.info(f"Review email request: {len(request.email_content)} characters")

        context = {
            "mode": "review",
            "email_content": request.email_content,
            "recipient_country": request.recipient_country or "Unknown",
            "purpose": request.purpose
        }

        # Run agent in thread pool to avoid blocking event loop
        result = await asyncio.to_thread(
            agent.run,
            user_input="",  # Not needed for review mode
            context=context
        )

        # Convert AgentResponse to dict for EmailResponse
        return EmailResponse(**result.to_dict())

    except Exception as e:
        logger.error(f"Review email failed: {e}")
        raise HTTPException(status_code=500, detail=f"Email review failed: {str(e)}")
