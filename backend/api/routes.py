"""
API Routes
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any

from backend.agents.orchestrator import Orchestrator # Import the Orchestrator

router = APIRouter()

# Instantiate the Orchestrator globally
orchestrator = Orchestrator()


class ChatRequest(BaseModel):
    """Chat request model"""
    session_id: str # Added session_id
    message: str
    context: Optional[Dict[str, Any]] = None


class ChatResponse(BaseModel):
    """Chat response model"""
    response: str
    agent_type: str
    metadata: Optional[Dict[str, Any]] = None


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Main chat endpoint - routes to appropriate agent based on intent
    """
    orchestrator_result = orchestrator.run(
        session_id=request.session_id,
        user_input=request.message,
        context=request.context
    )
    
    # The orchestrator_result is already in the format expected by ChatResponse
    return ChatResponse(**orchestrator_result["response"])


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
