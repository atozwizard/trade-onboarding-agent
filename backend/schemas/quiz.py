# backend/schemas/quiz.py

from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class QuizQuestion(BaseModel):
    """Single quiz question structure"""
    quiz_id: str = Field(..., description="Unique ID for this question")
    question: str = Field(..., description="Question text")
    choices: List[str] = Field(..., description="List of answer choices (4 options)")
    correct_answer: int = Field(..., description="Index of correct answer (0-3)", ge=0, le=3)
    explanation: str = Field(..., description="Explanation for the correct answer")
    quiz_type: str = Field(default="term_to_description", description="Quiz type")
    difficulty: str = Field(default="easy", description="Difficulty level: easy, medium, hard")
    term: Optional[str] = Field(None, description="Key term being tested")


class QuizStartRequest(BaseModel):
    """Request to start a new quiz session"""
    topic: Optional[str] = Field(None, description="Topic filter (e.g., 'Incoterms', 'payment')")
    difficulty: Optional[str] = Field(None, description="Difficulty: easy, medium, hard, or null for mixed")
    count: int = Field(5, description="Number of questions", ge=1, le=10)


class QuizStartResponse(BaseModel):
    """Response with generated quiz questions"""
    quiz_session_id: str = Field(..., description="Unique session ID for this quiz")
    questions: List[dict] = Field(..., description="List of questions (without answers)")
    total_questions: int = Field(..., description="Total number of questions")
    topic: Optional[str] = None
    difficulty: Optional[str] = None
    created_at: str = Field(..., description="ISO timestamp")


class QuizAnswerRequest(BaseModel):
    """Request to submit an answer"""
    quiz_session_id: str = Field(..., description="Quiz session ID")
    quiz_id: str = Field(..., description="Question ID")
    answer: int = Field(..., description="Selected answer index (0-3)", ge=0, le=3)


class QuizAnswerResponse(BaseModel):
    """Response with answer evaluation"""
    quiz_id: str
    is_correct: bool
    user_answer: int
    correct_answer: int
    explanation: str
    question: str
    choices: List[str]
