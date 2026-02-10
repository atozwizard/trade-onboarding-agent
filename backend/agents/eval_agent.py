"""
퀴즈 품질 평가 에이전트
- 생성된 퀴즈를 원본 데이터와 대조하여 검증
- grounding / educational / insight 3개 축으로 평가
"""
import json
from pathlib import Path
from typing import Dict, Any

from backend.utils.llm import call_llm

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATASET_DIR = BASE_DIR / "dataset"
PROMPTS_DIR = BASE_DIR / "backend" / "prompts"

# 퀴즈 주제별 대조용 데이터 파일
TOPIC_FILE_MAP = {
    "general": ["quiz_samples.json", "trade_qa.json"],
    "mistakes": ["mistakes.json", "document_errors.json"],
    "negotiation": ["negotiation.json"],
    "country": ["country_rules.json"],
    "documents": ["document_errors.json"],
}


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
    """평가 프롬프트 템플릿을 파일에서 읽어온다."""
    prompt_path = PROMPTS_DIR / "eval_prompt.txt"
    with open(prompt_path, "r", encoding="utf-8") as f:
        return f.read()


def _build_reference_text(dataset: list[Dict[str, Any]]) -> str:
    """원본 데이터셋 전체를 대조용 텍스트로 변환한다."""
    lines = []
    for item in dataset:
        content = item.get("content", "")
        metadata = item.get("metadata", {})
        if metadata:
            detail = " | ".join(f"{k}: {v}" for k, v in metadata.items() if v)
            lines.append(f"- {content} ({detail})" if detail else f"- {content}")
        else:
            lines.append(f"- {content}")
    return "\n".join(lines)


def _parse_eval_json(raw: str) -> Dict[str, Any]:
    """LLM 응답에서 평가 JSON을 파싱한다."""
    text = raw.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines)
    return json.loads(text)


def _validate_eval_result(result: Dict[str, Any]) -> Dict[str, Any]:
    """평가 결과의 구조와 is_passed 로직을 검증/보정한다."""
    gs = max(0, min(10, int(result.get("grounding_score", 0))))
    es = max(0, min(10, int(result.get("educational_score", 0))))
    ins = max(0, min(10, int(result.get("insight_score", 0))))

    total_ratio = (gs + es + ins) / 30
    is_passed = total_ratio >= 0.8 and gs == 10

    return {
        "grounding_score": gs,
        "educational_score": es,
        "insight_score": ins,
        "is_passed": is_passed,
        "feedback": result.get("feedback", ""),
    }


async def evaluate_quiz(
    quiz_data: Dict[str, Any],
    topic: str = "general",
) -> Dict[str, Any]:
    """퀴즈 품질을 평가하고 검증 리포트를 반환한다.

    Args:
        quiz_data: 퀴즈 데이터 (question, choices, answer, explanation 포함)
        topic: 퀴즈 주제 (원본 데이터 대조용)

    Returns:
        {"response": {평가 결과 JSON}, "agent_type": "eval", "metadata": {...}}
    """
    # 1) 주제에 맞는 원본 데이터 로드
    filenames = TOPIC_FILE_MAP.get(topic, TOPIC_FILE_MAP["general"])
    dataset = _load_dataset(filenames)

    if not dataset:
        return {
            "response": {"error": "대조용 데이터셋을 찾을 수 없습니다."},
            "agent_type": "eval",
            "metadata": {"topic": topic},
        }

    # 2) 프롬프트 조립
    reference_text = _build_reference_text(dataset)
    quiz_text = json.dumps(quiz_data, ensure_ascii=False, indent=2)

    template = _load_prompt_template()
    system_prompt = (
        template
        .replace("{quiz_data}", quiz_text)
        .replace("{reference_data}", reference_text)
    )

    # 3) LLM 호출
    raw_response = await call_llm(
        user_message="위 퀴즈를 원본 데이터와 대조하여 엄격하게 평가해주세요.",
        system_prompt=system_prompt,
        temperature=0.3,
    )

    # 4) JSON 파싱 및 검증
    try:
        eval_result = _parse_eval_json(raw_response)
        eval_result = _validate_eval_result(eval_result)
    except (json.JSONDecodeError, KeyError, ValueError) as e:
        return {
            "response": {"error": f"평가 결과 파싱 실패: {str(e)}", "raw": raw_response},
            "agent_type": "eval",
            "metadata": {"topic": topic},
        }

    return {
        "response": eval_result,
        "agent_type": "eval",
        "metadata": {"topic": topic},
    }
