"""
퀴즈 품질 평가 에이전트 (RAG 기반)
- 생성된 퀴즈를 RAG 검색된 원본 데이터와 대조하여 검증
- grounding / educational / insight 3개 축으로 평가
"""
import json
import os
from typing import Dict, Any

from backend.utils.llm import call_llm
from backend.rag.retriever import search_with_filter

# 프롬프트 파일 경로
PROMPTS_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), '..', 'prompts'
)


def _load_prompt(filename: str) -> str:
    """프롬프트 파일을 읽어온다."""
    prompt_path = os.path.join(PROMPTS_DIR, filename)
    with open(prompt_path, "r", encoding="utf-8") as f:
        return f.read()


def _parse_eval_json(raw: str) -> Dict[str, Any]:
    """LLM 응답에서 평가 JSON을 파싱한다."""
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


class EvalAgent:
    """RAG 기반 퀴즈 품질 평가 에이전트"""

    agent_type: str = "eval"

    def __init__(self):
        self.system_prompt = _load_prompt("eval_prompt.txt")

    async def run(self, user_input: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """퀴즈 품질을 평가한다."""
        quiz_data = context.get("quiz_data", {})
        topic = context.get("topic", "general")
        return await self.evaluate_quiz(quiz_data, topic)

    async def evaluate_quiz(
        self, quiz_data: Dict[str, Any], topic: str = "general"
    ) -> Dict[str, Any]:
        """퀴즈 품질을 평가하고 검증 리포트를 반환한다."""
        # 1) 퀴즈 문제로 RAG 검색 (관련 원본 데이터)
        question = quiz_data.get("question", "")
        docs = search_with_filter(query=question, k=5)

        # 2) 참고 데이터 포맷
        reference_data = _format_reference_data(docs)

        # 3) 프롬프트 조립
        quiz_text = json.dumps(quiz_data, ensure_ascii=False, indent=2)
        prompt = (
            self.system_prompt
            .replace("{quiz_data}", quiz_text)
            .replace("{reference_data}", reference_data)
        )

        # 4) LLM 호출 (낮은 temperature로 일관된 평가)
        raw_response = await call_llm(
            user_message="위 퀴즈를 원본 데이터와 대조하여 엄격하게 평가해주세요.",
            system_prompt=prompt,
            temperature=0.3,
        )

        # 5) JSON 파싱 및 검증
        try:
            eval_result = _parse_eval_json(raw_response)
            eval_result = _validate_eval_result(eval_result)
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            return {
                "response": {"error": f"평가 결과 파싱 실패: {str(e)}", "raw": raw_response},
                "agent_type": self.agent_type,
                "metadata": {"topic": topic},
            }

        return {
            "response": eval_result,
            "agent_type": self.agent_type,
            "metadata": {"topic": topic},
        }
