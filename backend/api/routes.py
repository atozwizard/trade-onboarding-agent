"""
API Routes
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any

from backend.schemas.agent_response import ChatResponse # Import the new ChatResponse schema
from backend.schemas.quiz import (
    QuizStartRequest,
    QuizStartResponse,
    QuizAnswerRequest,
    QuizAnswerResponse
)
from backend.agents.orchestrator.graph import orchestrator_graph # Import the orchestrator graph
from backend.agents.orchestrator.state import OrchestratorGraphState # Import the state definition
from backend.services.quiz_service import quiz_session_store, quiz_generator

router = APIRouter()

# Compile the orchestrator graph globally
compiled_orchestrator_app = orchestrator_graph.compile()


class ChatRequest(BaseModel):
    """Chat request model"""
    session_id: str # Added session_id
    message: str
    context: Optional[Dict[str, Any]] = None


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Main chat endpoint - routes to appropriate agent based on intent
    """
    # Initial state for the graph
    initial_state: OrchestratorGraphState = {
        "session_id": request.session_id,
        "user_input": request.message,
        "context": request.context if request.context is not None else {},
        "conversation_history": [], # Will be loaded by load_session_state_node
        "active_agent": None,      # Will be loaded by load_session_state_node
        "agent_specific_state": {},# Will be loaded by load_session_state_node
        "orchestrator_response": None,
        "llm_intent_classification": None,
        "selected_agent_name": None
    }
    
    # Invoke the compiled graph
    orchestrator_result = await compiled_orchestrator_app.ainvoke(initial_state)
    
    # The orchestrator_result is the final output of the graph (normalize_response_node)
    return ChatResponse(**orchestrator_result)


@router.post("/quiz/start", response_model=QuizStartResponse)
async def start_quiz(request: QuizStartRequest):
    """
    Start a new quiz session.

    Generates quiz questions and creates a session to track answers.

    Args:
        request: QuizStartRequest with optional topic, difficulty, and count

    Returns:
        QuizStartResponse with quiz_session_id and questions (without answers)
    """
    try:
        # Generate quiz questions
        questions = quiz_generator.generate_sample_quizzes(
            count=request.count,
            topic=request.topic,
            difficulty=request.difficulty
        )

        # Create session
        session_id = quiz_session_store.create_session(
            questions=questions,
            topic=request.topic,
            difficulty=request.difficulty
        )

        # Prepare response (hide correct answers and explanations)
        questions_for_user = [
            {
                "quiz_id": q.quiz_id,
                "question": q.question,
                "choices": q.choices,
                "quiz_type": q.quiz_type,
                "difficulty": q.difficulty
            }
            for q in questions
        ]

        return QuizStartResponse(
            quiz_session_id=session_id,
            questions=questions_for_user,
            total_questions=len(questions),
            topic=request.topic,
            difficulty=request.difficulty,
            created_at=quiz_session_store.get_session(session_id)["created_at"]
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate quiz: {str(e)}")


@router.post("/quiz/answer", response_model=QuizAnswerResponse)
async def answer_quiz(request: QuizAnswerRequest):
    """
    Submit an answer for a quiz question.

    Evaluates the answer and returns immediate feedback.

    Args:
        request: QuizAnswerRequest with quiz_session_id, quiz_id, and answer

    Returns:
        QuizAnswerResponse with evaluation result
    """
    try:
        # Get question from session
        question = quiz_session_store.get_question(
            request.quiz_session_id,
            request.quiz_id
        )

        if not question:
            raise HTTPException(
                status_code=404,
                detail=f"Question {request.quiz_id} not found in session {request.quiz_session_id}"
            )

        # Save user answer
        quiz_session_store.save_answer(
            request.quiz_session_id,
            request.quiz_id,
            request.answer
        )

        # Evaluate answer
        is_correct = request.answer == question.correct_answer

        return QuizAnswerResponse(
            quiz_id=request.quiz_id,
            is_correct=is_correct,
            user_answer=request.answer,
            correct_answer=question.correct_answer,
            explanation=question.explanation,
            question=question.question,
            choices=question.choices
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to evaluate answer: {str(e)}")
