"""
퀴즈 학습 에이전트
- dataset/ JSON 파일을 직접 읽어 퀴즈 소스로 활용
- call_llm을 통해 4지선다 퀴즈 생성 및 답안 평가
"""
import json
import random
import uuid
from pathlib import Path
from typing import Dict, Any, Optional

from backend.utils.llm import call_llm

# 프로젝트 루트 기준 경로
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATASET_DIR = BASE_DIR / "dataset"
PROMPTS_DIR = BASE_DIR / "backend" / "prompts"

# 주제별 데이터 파일 매핑
TOPIC_FILE_MAP = {
    "general": ["quiz_samples.json", "trade_qa.json"],
    "mistakes": ["mistakes.json", "document_errors.json"],
    "negotiation": ["negotiation.json"],
    "country": ["country_rules.json"],
    "documents": ["document_errors.json"],
}

# 생성된 퀴즈를 임시 저장 (quiz_id -> quiz_data)
_quiz_store: Dict[str, Dict[str, Any]] = {}


def _load_dataset(filenames: list[str]) -> list[Dict[str, Any]]:
    """dataset/ 디렉토리에서 JSON 파일들을 직접 읽어온다."""
    data = []
    for filename in filenames:
        filepath = DATASET_DIR / filename
        if filepath.exists():
            with open(filepath, "r", encoding="utf-8") as f:
                items = json.load(f)
                data.extend(items)
    return data


def _load_prompt_template() -> str:
    """프롬프트 템플릿을 파일에서 읽어온다."""
    prompt_path = PROMPTS_DIR / "quiz_prompt.txt"
    with open(prompt_path, "r", encoding="utf-8") as f:
        return f.read()


def _sample_reference_data(dataset: list[Dict[str, Any]], count: int = 5) -> str:
    """데이터셋에서 랜덤 샘플링하여 참고 데이터 문자열로 변환한다."""
    samples = random.sample(dataset, min(count, len(dataset)))
    lines = []
    for item in samples:
        content = item.get("content", "")
        metadata = item.get("metadata", {})
        if metadata:
            detail = " | ".join(f"{k}: {v}" for k, v in metadata.items() if v)
            lines.append(f"- {content} ({detail})" if detail else f"- {content}")
        else:
            lines.append(f"- {content}")
    return "\n".join(lines)


def _parse_quiz_json(raw: str) -> Dict[str, Any]:
    """LLM 응답에서 JSON을 파싱한다. 코드블록 감싸기 등을 처리."""
    text = raw.strip()
    # ```json ... ``` 블록 제거
    if text.startswith("```"):
        lines = text.split("\n")
        # 첫 줄(```json)과 마지막 줄(```) 제거
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines)
    return json.loads(text)


async def generate_quiz(
    topic: str = "general",
    difficulty: str = "easy",
) -> Dict[str, Any]:
    """퀴즈를 생성하고 결과를 반환한다.

    Args:
        topic: 주제 (general, mistakes, negotiation, country, documents)
        difficulty: 난이도 (easy, medium, hard)

    Returns:
        {"response": {...quiz_data}, "agent_type": "quiz", "metadata": {...}}
    """
    # 1) 주제에 맞는 데이터 로드
    filenames = TOPIC_FILE_MAP.get(topic, TOPIC_FILE_MAP["general"])
    dataset = _load_dataset(filenames)

    if not dataset:
        return {
            "response": {"error": "데이터셋을 찾을 수 없습니다."},
            "agent_type": "quiz",
            "metadata": {"topic": topic, "difficulty": difficulty},
        }

    # 2) 참고 데이터 샘플링
    reference_data = _sample_reference_data(dataset, count=5)

    # 3) 프롬프트 조립
    template = _load_prompt_template()
    system_prompt = (
        template
        .replace("{reference_data}", reference_data)
        .replace("{topic}", topic)
        .replace("{difficulty}", difficulty)
    )

    # 4) LLM 호출
    raw_response = await call_llm(
        user_message="위 조건에 맞는 무역 퀴즈 1문제를 JSON으로 출제해주세요.",
        system_prompt=system_prompt,
    )

    # 5) JSON 파싱
    try:
        quiz_data = _parse_quiz_json(raw_response)
    except (json.JSONDecodeError, KeyError):
        return {
            "response": {"error": "퀴즈 생성에 실패했습니다. 다시 시도해주세요."},
            "agent_type": "quiz",
            "metadata": {"topic": topic, "difficulty": difficulty, "raw": raw_response},
        }

    # 6) 퀴즈 저장 (채점용)
    quiz_id = str(uuid.uuid4())[:8]
    _quiz_store[quiz_id] = quiz_data

    return {
        "response": {
            "quiz_id": quiz_id,
            "question": quiz_data["question"],
            "choices": quiz_data["choices"],
        },
        "agent_type": "quiz",
        "metadata": {"topic": topic, "difficulty": difficulty},
    }


async def evaluate_answer(
    quiz_id: str,
    user_answer: int,
) -> Dict[str, Any]:
    """사용자 답안을 채점하고 해설을 반환한다.

    Args:
        quiz_id: 퀴즈 ID
        user_answer: 사용자가 선택한 보기 인덱스 (0~3)

    Returns:
        {"response": {...result}, "agent_type": "quiz", "metadata": {...}}
    """
    quiz_data = _quiz_store.get(quiz_id)

    if not quiz_data:
        return {
            "response": {"error": f"퀴즈 ID '{quiz_id}'를 찾을 수 없습니다."},
            "agent_type": "quiz",
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
        "agent_type": "quiz",
        "metadata": {"quiz_id": quiz_id},
    }
