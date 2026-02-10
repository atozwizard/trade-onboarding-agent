"""
API Routes
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

from backend.agents.quiz_agent import generate_quiz, evaluate_answer

router = APIRouter()


class ChatRequest(BaseModel):
    """Chat request model"""
    message: str
    context: Optional[Dict[str, Any]] = None


class ChatResponse(BaseModel):
    """Chat response model"""
    response: str
    agent_type: str
    metadata: Optional[Dict[str, Any]] = None


class QuizRequest(BaseModel):
    """퀴즈 생성 요청"""
    topic: str = Field(default="general", description="주제: general, mistakes, negotiation, country, documents")
    difficulty: str = Field(default="easy", description="난이도: easy, medium, hard")


class QuizAnswerRequest(BaseModel):
    """퀴즈 답안 제출 요청"""
    quiz_id: str
    answer: int = Field(ge=0, le=3, description="선택한 보기 인덱스 (0~3)")


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


@router.post("/quiz/start")
async def start_quiz(request: QuizRequest):
    """퀴즈를 생성하여 반환한다."""
    result = await generate_quiz(
        topic=request.topic,
        difficulty=request.difficulty,
    )

    if "error" in result["response"]:
        raise HTTPException(status_code=500, detail=result["response"]["error"])

    return result


@router.post("/quiz/answer")
async def answer_quiz(request: QuizAnswerRequest):
    """퀴즈 답안을 채점하고 해설을 반환한다."""
    result = await evaluate_answer(
        quiz_id=request.quiz_id,
        user_answer=request.answer,
    )

    if "error" in result["response"]:
        raise HTTPException(status_code=404, detail=result["response"]["error"])

    return result
