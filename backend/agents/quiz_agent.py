"""
퀴즈 학습 에이전트 (RAG 기반)
- RAG 검색으로 참고 데이터를 가져와 퀴즈 소스로 활용
- call_llm을 통해 4지선다 퀴즈 생성 및 답안 평가
"""
import json
import uuid
import os
from typing import Dict, Any, Optional

from backend.utils.llm import call_llm
from backend.rag.retriever import search_with_filter

# 프롬프트 파일 경로
PROMPTS_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), '..', 'prompts'
)

# 주제별 RAG 필터 매핑
TOPIC_FILTER_MAP: Dict[str, Dict[str, Optional[str]]] = {
    "general": {},
    "mistakes": {"document_type": "common_mistake"},
    "negotiation": {"document_type": "negotiation_strategy"},
    "country": {"document_type": "country_guideline"},
    "documents": {"document_type": "error_checklist"},
}

# 난이도 → level 매핑
DIFFICULTY_LEVEL_MAP: Dict[str, str] = {
    "easy": "beginner",
    "medium": "working",
    "hard": "manager",
}

# 생성된 퀴즈를 임시 저장 (quiz_id -> quiz_data)
_quiz_store: Dict[str, Dict[str, Any]] = {}


def _load_prompt(filename: str) -> str:
    """프롬프트 파일을 읽어온다."""
    prompt_path = os.path.join(PROMPTS_DIR, filename)
    with open(prompt_path, "r", encoding="utf-8") as f:
        return f.read()


def _parse_quiz_json(raw: str) -> Dict[str, Any]:
    """LLM 응답에서 JSON을 파싱한다."""
    text = raw.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines)
    return json.loads(text)


def _format_reference_data(docs: list) -> str:
    """RAG 검색 결과를 참고 데이터 텍스트로 포맷한다."""
    if not docs:
        return "(참고 데이터 없음)"
    lines = []
    for doc in docs:
        content = doc.get("document", "")
        metadata = doc.get("metadata", {})
        if metadata:
            detail = " | ".join(
                f"{k}: {v}" for k, v in metadata.items() if v
            )
            lines.append(f"- {content} ({detail})" if detail else f"- {content}")
        else:
            lines.append(f"- {content}")
    return "\n".join(lines)


class QuizAgent:
    """RAG 기반 퀴즈 학습 에이전트"""

    agent_type: str = "quiz"

    def __init__(self):
        self.system_prompt = _load_prompt("quiz_prompt.txt")

    async def run(self, user_input: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """context["action"]에 따라 퀴즈 생성 또는 답안 채점을 수행한다."""
        action = context.get("action", "generate")

        if action == "generate":
            topic = context.get("topic", "general")
            difficulty = context.get("difficulty", "easy")
            return await self._generate_quiz(topic, difficulty)
        elif action == "evaluate":
            quiz_id = context.get("quiz_id", "")
            user_answer = context.get("user_answer", 0)
            return self._evaluate_answer(quiz_id, user_answer)
        else:
            return {
                "response": f"알 수 없는 action: {action}",
                "agent_type": self.agent_type,
                "metadata": {},
            }

    async def _generate_quiz(self, topic: str, difficulty: str) -> Dict[str, Any]:
        """RAG 검색 + LLM을 사용하여 퀴즈를 생성한다."""
        # 1) RAG 필터 구성
        filters = TOPIC_FILTER_MAP.get(topic, {}).copy()
        level = DIFFICULTY_LEVEL_MAP.get(difficulty, "beginner")
        filters["level"] = level

        # 2) RAG 검색
        query = f"{topic} 무역 퀴즈 {difficulty}"
        docs = search_with_filter(query=query, k=5, **filters)

        # 3) 참고 데이터 포맷
        reference_data = _format_reference_data(docs)

        # 4) 프롬프트 조립
        prompt = (
            self.system_prompt
            .replace("{reference_data}", reference_data)
            .replace("{topic}", topic)
            .replace("{difficulty}", difficulty)
        )

        # 5) LLM 호출
        raw_response = await call_llm(
            user_message="위 조건에 맞는 무역 퀴즈 1문제를 JSON으로 출제해주세요.",
            system_prompt=prompt,
        )

        # 6) JSON 파싱
        try:
            quiz_data = _parse_quiz_json(raw_response)
        except (json.JSONDecodeError, KeyError):
            return {
                "response": {"error": "퀴즈 생성에 실패했습니다. 다시 시도해주세요."},
                "agent_type": self.agent_type,
                "metadata": {"topic": topic, "difficulty": difficulty, "raw": raw_response},
            }

        # 7) 퀴즈 저장 (채점용)
        quiz_id = str(uuid.uuid4())[:8]
        _quiz_store[quiz_id] = quiz_data

        return {
            "response": {
                "quiz_id": quiz_id,
                "question": quiz_data["question"],
                "choices": quiz_data["choices"],
            },
            "agent_type": self.agent_type,
            "metadata": {"topic": topic, "difficulty": difficulty},
        }

    def _evaluate_answer(self, quiz_id: str, user_answer: int) -> Dict[str, Any]:
        """사용자 답안을 채점하고 해설을 반환한다."""
        quiz_data = _quiz_store.get(quiz_id)

        if not quiz_data:
            return {
                "response": {"error": f"퀴즈 ID '{quiz_id}'를 찾을 수 없습니다."},
                "agent_type": self.agent_type,
                "metadata": {"quiz_id": quiz_id},
            }

        correct_answer = quiz_data["answer"]
        is_correct = user_answer == correct_answer

        return {
            "response": {
                "quiz_id": quiz_id,
                "is_correct": is_correct,
                "user_answer": user_answer,
                "correct_answer": correct_answer,
                "correct_choice": quiz_data["choices"][correct_answer],
                "explanation": quiz_data["explanation"],
            },
            "agent_type": self.agent_type,
            "metadata": {"quiz_id": quiz_id},
        }
