"""
퀴즈 품질 평가 에이전트 (RAG 기반)

[역할]
  QuizAgent가 생성한 퀴즈가 "쓸 만한 퀴즈인지" 자동으로 검증하는 에이전트.
  LLM이 만든 퀴즈를 원본 데이터와 비교해서 사실 오류, 교육 적합도, 실무 팁 품질을 채점한다.

[전체 흐름]
  사용자가 POST /quiz/evaluate 요청
    → routes.py에서 _quiz_store에서 퀴즈 데이터 조회
    → EvalAgent.run() 호출
        1) 퀴즈 문제 텍스트로 ChromaDB RAG 검색 → 관련 원본 데이터 확보
        2) 퀴즈 데이터 + 원본 데이터를 eval_prompt.txt에 삽입
        3) LLM이 3가지 축(grounding, educational, insight)으로 점수 산출
        4) _validate_eval_result()로 점수 보정 및 pass/fail 판정
    → 평가 리포트 반환

[평가 기준 요약]
  - grounding_score (0~10): 원본 데이터와 사실이 맞는지
  - educational_score (0~10): 신입사원 교육에 적합한지
  - insight_score (0~10): 실무 팁이 포함되어 있는지
  - is_passed: 평균 80% 이상 AND grounding 만점이면 통과
"""
import json
import os
from typing import Dict, Any

from langsmith import traceable  # LangSmith 트레이싱 데코레이터

# call_llm: Upstage Solar LLM에 프롬프트를 보내고 응답 텍스트를 받는 함수
from backend.utils.llm import call_llm
# search_with_filter: ChromaDB에서 메타데이터 필터 조건으로 유사 문서를 검색하는 함수
from backend.rag.retriever import search_with_filter

# ──────────────────────────────────────────────
# 상수 정의
# ──────────────────────────────────────────────

# 프롬프트 파일이 위치한 디렉토리 경로
PROMPTS_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), '..', 'prompts'
)


# ──────────────────────────────────────────────
# 유틸리티 함수
# ──────────────────────────────────────────────

def _load_prompt(filename: str) -> str:
    """프롬프트 템플릿 파일(.txt)을 읽어서 문자열로 반환한다.
    반환된 문자열에는 {quiz_data}, {reference_data} 플레이스홀더가 포함되어 있다.
    """
    prompt_path = os.path.join(PROMPTS_DIR, filename)
    with open(prompt_path, "r", encoding="utf-8") as f:
        return f.read()


def _parse_eval_json(raw: str) -> Dict[str, Any]:
    """LLM이 반환한 텍스트에서 평가 결과 JSON을 추출하여 파싱한다.
    ```json ... ``` 코드블록 감싸기를 제거한 후 파싱한다.

    예시 입력:
        ```json
        {"grounding_score": 10, "educational_score": 8, ...}
        ```
    → {"grounding_score": 10, "educational_score": 8, ...} (dict)
    """
    text = raw.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines)
    return json.loads(text)


def _format_reference_data(docs: list) -> str:
    """RAG 검색 결과(문서 리스트)를 LLM에게 넘길 텍스트 형태로 변환한다.
    quiz_agent.py의 동일 함수와 같은 로직.

    출력 예시:
        - FOB는 수출자가 ... (topic: incoterms | level: beginner)
        - CIF 조건에서는 ... (topic: incoterms | level: working)
    """
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
    """LLM이 반환한 평가 결과를 검증하고 보정한다.

    하는 일:
      1) 각 점수를 0~10 범위로 클램핑 (LLM이 범위를 벗어난 값을 줄 수 있으므로)
      2) is_passed를 서버 측에서 재계산 (LLM의 판단을 신뢰하지 않고 직접 계산)
         - 통과 조건: 3개 점수 합산 평균이 80% 이상 AND grounding이 만점(10)
         - 즉, 사실 오류가 하나라도 있으면 (grounding < 10) 무조건 불합격

    Args:
        result: LLM이 반환한 평가 JSON (grounding_score, educational_score, ...)

    Returns:
        보정된 평가 결과 딕셔너리
    """
    # 각 점수를 정수로 변환하고 0~10 범위로 제한
    gs = max(0, min(10, int(result.get("grounding_score", 0))))    # 원본 일치도
    es = max(0, min(10, int(result.get("educational_score", 0))))  # 교육 적합도
    ins = max(0, min(10, int(result.get("insight_score", 0))))     # 실무 팁 품질

    # 통과 판정: (합산/30) >= 0.8 이고 grounding이 만점이어야 통과
    total_ratio = (gs + es + ins) / 30
    is_passed = total_ratio >= 0.8 and gs == 10

    return {
        "grounding_score": gs,
        "educational_score": es,
        "insight_score": ins,
        "is_passed": is_passed,
        "feedback": result.get("feedback", ""),
    }


# ──────────────────────────────────────────────
# EvalAgent 클래스
# ──────────────────────────────────────────────

class EvalAgent:
    """RAG 기반 퀴즈 품질 평가 에이전트

    routes.py에서 싱글톤으로 생성되어 사용된다:
        eval_agent = EvalAgent()
        result = await eval_agent.run("퀴즈 평가", {"quiz_data": {...}, "topic": "general"})
    """

    agent_type: str = "eval"

    def __init__(self):
        # 서버 시작 시 평가 프롬프트 템플릿을 한 번만 파일에서 읽어 메모리에 보관
        self.system_prompt = _load_prompt("eval_prompt.txt")

    async def run(self, user_input: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """에이전트 진입점.
        context에서 quiz_data(평가 대상 퀴즈)와 topic(원본 대조용 주제)을 꺼내서 evaluate_quiz()를 호출한다.
        """
        quiz_data = context.get("quiz_data", {})
        topic = context.get("topic", "general")
        return await self.evaluate_quiz(quiz_data, topic)

    @traceable(name="eval_quiz_quality", run_type="chain")
    async def evaluate_quiz(
        self, quiz_data: Dict[str, Any], topic: str = "general"
    ) -> Dict[str, Any]:
        """퀴즈 품질을 평가하고 검증 리포트를 반환한다.

        파이프라인:
            1) 퀴즈 문제 텍스트로 ChromaDB 검색 → 관련 원본 문서 확보
            2) 원본 문서를 텍스트로 포맷
            3) eval_prompt.txt에 퀴즈 데이터 + 원본 데이터 삽입
            4) LLM 호출 (temperature=0.3으로 일관된 평가를 유도)
            5) JSON 파싱 → _validate_eval_result()로 점수 보정 및 pass/fail 재계산
        """
        # 1) 퀴즈의 question 텍스트를 검색어로 사용하여 관련 원본 데이터 검색
        #    필터 없이 검색 → 퀴즈 내용과 가장 유사한 원본 문서를 찾기 위함
        question = quiz_data.get("question", "")
        docs = search_with_filter(query=question, k=5)

        # 2) 검색된 원본 문서들을 텍스트로 변환
        reference_data = _format_reference_data(docs)

        # 3) 프롬프트 조립
        #    퀴즈 데이터를 JSON 문자열로 변환하여 프롬프트에 삽입
        quiz_text = json.dumps(quiz_data, ensure_ascii=False, indent=2)
        prompt = (
            self.system_prompt
            .replace("{quiz_data}", quiz_text)
            .replace("{reference_data}", reference_data)
        )

        # 4) LLM 호출
        #    temperature=0.3: 평가는 창의성보다 일관성이 중요하므로 낮은 온도 사용
        raw_response = await call_llm(
            user_message="위 퀴즈를 원본 데이터와 대조하여 엄격하게 평가해주세요.",
            system_prompt=prompt,
            temperature=0.3,
        )

        # 5) JSON 파싱 → 점수 보정 → pass/fail 재계산
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
