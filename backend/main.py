"""
FastAPI Main Application
TradeOnboarding Agent Backend
"""

import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any
from dotenv import load_dotenv

# Import agents
from agents.orchestrator import AgentOrchestrator
from agents.quiz_agent import QuizAgent
from agents.email_agent import EmailAgent
from agents.mistake_agent import MistakeAgent
from agents.ceo_agent import CEOAgent

load_dotenv()

# Initialize FastAPI app
app = FastAPI(
    title="TradeOnboarding Agent API",
    description="AI-powered onboarding simulator for trading company employees",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize orchestrator and agents
orchestrator = AgentOrchestrator()
quiz_agent = QuizAgent()
email_agent = EmailAgent()
mistake_agent = MistakeAgent()
ceo_agent = CEOAgent()

# Register agents
orchestrator.register_agent("quiz", quiz_agent)
orchestrator.register_agent("email", email_agent)
orchestrator.register_agent("mistake", mistake_agent)
orchestrator.register_agent("ceo", ceo_agent)


# Request/Response Models
class ChatRequest(BaseModel):
    message: str
    context: Optional[Dict[str, Any]] = None


class ChatResponse(BaseModel):
    response: str
    agent_type: str
    metadata: Optional[Dict[str, Any]] = None


class QuizRequest(BaseModel):
    topic: Optional[str] = "general"


class QuizSubmitRequest(BaseModel):
    quiz_id: str
    answer: str


class EmailRequest(BaseModel):
    email_draft: str


# Health check
@app.get("/")
async def root():
    return {
        "message": "TradeOnboarding Agent API",
        "status": "running",
        "version": "1.0.0"
    }


@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "agents": list(orchestrator.agents.keys())
    }


# Main chat endpoint
@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Main chat endpoint - routes to appropriate agent
    """
    try:
        result = orchestrator.route(request.message, request.context)
        
        return ChatResponse(
            response=result.get("response", ""),
            agent_type=result.get("agent_type", "general"),
            metadata=result.get("metadata", {})
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Quiz endpoints
@app.post("/api/quiz/generate")
async def generate_quiz(request: QuizRequest):
    """Generate a new quiz"""
    try:
        topic = request.topic or "무역 용어"
        result = quiz_agent.run(f"{topic}에 대한 퀴즈를 내줘")
        
        return {
            "quiz": result.get("response", ""),
            "metadata": result.get("metadata", {})
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/quiz/submit")
async def submit_quiz_answer(request: QuizSubmitRequest):
    """Submit quiz answer for evaluation"""
    try:
        # This would need quiz state management in production
        return {
            "message": "Quiz submission endpoint - requires state management",
            "quiz_id": request.quiz_id,
            "answer": request.answer
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Email coaching endpoint
@app.post("/api/email/coach")
async def coach_email(request: EmailRequest):
    """Get feedback on email draft"""
    try:
        result = email_agent.run(request.email_draft)
        
        return {
            "feedback": result.get("response", ""),
            "metadata": result.get("metadata", {})
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Mistake prediction endpoint
@app.post("/api/mistake/predict")
async def predict_mistakes(request: ChatRequest):
    """Predict potential mistakes for a situation"""
    try:
        result = mistake_agent.run(request.message)
        
        return {
            "predictions": result.get("response", ""),
            "metadata": result.get("metadata", {})
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# CEO simulator endpoint
@app.post("/api/ceo/simulate")
async def simulate_ceo(request: ChatRequest):
    """Simulate CEO interaction"""
    try:
        result = ceo_agent.run(request.message)
        
        return {
            "ceo_response": result.get("response", ""),
            "metadata": result.get("metadata", {})
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Agent info endpoint
@app.get("/api/agents")
async def get_agents():
    """Get information about available agents"""
    return orchestrator.get_agent_info()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
