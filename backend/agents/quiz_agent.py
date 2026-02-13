"""
용어 퀴즈 에이전트 (RAG 기반)

[전체 흐름]
  사용자 요청 → routes.py → QuizAgent.run()
    ├─ action="generate"
    │     1) RAG 검색 (정답 후보 + 오답 후보)
    │     2) LLM이 5문제 생성
    │     3) EvalTool로 문제별 검증
    │     4) 불합격 문제 재시도 (MAX_RETRY=2)
    │     5) 재시도 소진 시 다른 용어로 대체 생성
    │     6) 합격 풀 5문제 반환
    └─ action="evaluate" → 저장된 퀴즈에서 정답 비교

[퀴즈 유형]
  - 용어→설명: 용어가 문제, 설명 4개가 선택지
  - 설명→용어: 설명이 문제, 용어 4개가 선택지

[난이도]
  - 지정 시: 5문제 모두 해당 난이도
  - 미지정 시: easy 2 + medium 2 + hard 1 혼합
"""
import json
import uuid
import os
import logging
from typing import Dict, Any, Optional, List

from langsmith import traceable

from backend.utils.llm import call_llm
from backend.rag.retriever import search_with_filter
from backend.agents.eval_agent import evaluate_quiz_list

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
# 상수
# ──────────────────────────────────────────────

PROMPTS_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), '..', 'prompts'
)

MAX_RETRY = 2  # 불합격 문제 재시도 최대 횟수

# 퀴즈를 메모리에 임시 저장 (서버 재시작 시 초기화)
_quiz_store: Dict[str, Dict[str, Any]] = {}


# ──────────────────────────────────────────────
# 유틸리티
# ──────────────────────────────────────────────

def _load_prompt(filename: str) -> str:
    prompt_path = os.path.join(PROMPTS_DIR, filename)
    with open(prompt_path, "r", encoding="utf-8") as f:
        return f.read()


def _parse_quiz_json(raw: str) -> List[Dict[str, Any]]:
    """LLM 응답에서 JSON 배열 추출.
    앞뒤 텍스트, ```json ... ``` 코드블록 모두 처리.
    """
    import re
    text = raw.strip()

    # 1) 코드블록 내 JSON 추출 시도
    match = re.search(r'```(?:json)?\s*([\s\S]*?)```', text)
    if match:
        text = match.group(1).strip()

    # 2) 코드블록 없으면 [ ... ] 범위 추출
    if not text.startswith('[') and not text.startswith('{'):
        arr_match = re.search(r'(\[[\s\S]*\])', text)
        if arr_match:
            text = arr_match.group(1)

    parsed = json.loads(text)
    if isinstance(parsed, dict):
        parsed = [parsed]
    return parsed


def _format_reference_data(docs: list) -> str:
    """RAG 검색 결과를 텍스트로 변환."""
    if not docs:
        return "(참고 데이터 없음)"
    lines = []
    for doc in docs:
        content = doc.get("document", "")
        metadata = doc.get("metadata", {})
        if metadata:
            detail = " | ".join(f"{k}: {v}" for k, v in metadata.items() if v)
            lines.append(f"- {content} ({detail})" if detail else f"- {content}")
        else:
            lines.append(f"- {content}")
    return "\n".join(lines)


# ──────────────────────────────────────────────
# QuizAgent
# ──────────────────────────────────────────────

class QuizAgent:
    """RAG 기반 용어 퀴즈 에이전트

    사용법:
        quiz_agent = QuizAgent()
        result = await quiz_agent.run("퀴즈 생성", {"action": "generate", "difficulty": "easy"})
        result = await quiz_agent.run("답변", {"action": "evaluate", "quiz_id": "abc", "user_answer": 1})
    """

    agent_type: str = "quiz"

    def __init__(self):
        self.system_prompt = _load_prompt("quiz_prompt.txt")

    async def run(self, user_input: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """에이전트 진입점."""
        action = context.get("action", "generate")

        if action == "generate":
            difficulty = context.get("difficulty")
            return await self._generate_with_eval(difficulty)
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

    # ──────────────────────────────────────────
    # 핵심: 생성 → 검증 → 재시도 → 대체 생성 루프
    # ──────────────────────────────────────────

    @traceable(name="quiz_generate_with_eval", run_type="chain")
    async def _generate_with_eval(self, difficulty: Optional[str] = None) -> Dict[str, Any]:
        """합격한 5문제를 모을 때까지 생성-검증-재시도-대체 생성을 수행한다."""
        passed_quizzes: List[Dict[str, Any]] = []  # 합격 풀
        used_terms: List[str] = []                  # 사용된 용어 (대체 생성 시 제외용)
        retry_counts: Dict[str, int] = {}           # quiz_id별 재시도 횟수

        # ── 1단계: 최초 5문제 생성 ──
        quizzes = await self._generate_quizzes(
            count=5, difficulty=difficulty,
            exclude_terms=[], feedback_items=[]
        )
        if not quizzes:
            return self._error_response("퀴즈 생성에 실패했습니다.", difficulty)

        # 사용된 용어 기록
        for q in quizzes:
            used_terms.append(self._extract_term(q))

        # ── 2단계: EvalTool 검증 ──
        eval_results = await evaluate_quiz_list(quizzes)
        passed, failed = self._split_by_validity(quizzes, eval_results)
        passed_quizzes.extend(passed)

        # 재시도 카운트 초기화
        for q in failed:
            retry_counts[q["quiz_id"]] = 0

        # ── 3단계: 불합격 문제 재시도 루프 (MAX_RETRY=2) ──
        while failed and any(retry_counts.get(q["quiz_id"], 0) < MAX_RETRY for q in failed):
            # 재시도 횟수가 남은 문제만 필터
            retryable = [q for q in failed if retry_counts.get(q["quiz_id"], 0) < MAX_RETRY]
            if not retryable:
                break

            # 이전 실패 피드백 수집
            feedback_items = self._collect_feedback(retryable, eval_results)

            # 불합격 문제 수만큼 재생성
            regenerated = await self._generate_quizzes(
                count=len(retryable), difficulty=difficulty,
                exclude_terms=[], feedback_items=feedback_items
            )

            if regenerated:
                for q in regenerated:
                    used_terms.append(self._extract_term(q))

                # 재검증
                re_eval = await evaluate_quiz_list(regenerated)
                re_passed, re_failed = self._split_by_validity(regenerated, re_eval)
                passed_quizzes.extend(re_passed)

                # 재시도 카운트 업데이트
                # 재생성된 문제는 새 quiz_id를 가지므로 초기 카운트 1로 등록
                for q in retryable:
                    retry_counts[q["quiz_id"]] = retry_counts.get(q["quiz_id"], 0) + 1
                for q in re_failed:
                    if q["quiz_id"] not in retry_counts:
                        retry_counts[q["quiz_id"]] = 1

                # 여전히 불합격인 문제에 새로운 eval 결과 반영
                failed = re_failed
                eval_results = re_eval
            else:
                # 재생성 자체가 실패하면 카운트만 올리고 루프 종료
                for q in retryable:
                    retry_counts[q["quiz_id"]] = MAX_RETRY
                break

            # 5문제 달성 시 즉시 종료
            if len(passed_quizzes) >= 5:
                break

        # ── 4단계: 재시도 소진 후 대체 생성 ──
        remaining = 5 - len(passed_quizzes)
        if remaining > 0:
            logger.info(f"대체 생성 필요: {remaining}문제 (기존 용어 {len(used_terms)}개 제외)")
            replacement = await self._generate_quizzes(
                count=remaining, difficulty=difficulty,
                exclude_terms=used_terms, feedback_items=[]
            )
            if replacement:
                for q in replacement:
                    used_terms.append(self._extract_term(q))

                rep_eval = await evaluate_quiz_list(replacement)
                rep_passed, _ = self._split_by_validity(replacement, rep_eval)
                passed_quizzes.extend(rep_passed)

        # ── 5단계: 합격 풀에서 메모리 저장 & 응답 구성 ──
        final_quizzes = passed_quizzes[:5]
        response_list = []
        for q in final_quizzes:
            qid = q["quiz_id"]
            _quiz_store[qid] = q
            response_list.append({
                "quiz_id": qid,
                "question": q["question"],
                "choices": q["choices"],
                "quiz_type": q.get("quiz_type", ""),
                "difficulty": q.get("difficulty", difficulty or "mixed"),
            })

        return {
            "response": response_list,
            "agent_type": self.agent_type,
            "metadata": {
                "difficulty": difficulty,
                "count": len(response_list),
                "total_generated": len(used_terms),
            },
        }

    # ──────────────────────────────────────────
    # LLM 호출: 퀴즈 N문제 생성
    # ──────────────────────────────────────────

    @traceable(name="quiz_generate_batch", run_type="chain")
    async def _generate_quizzes(
        self,
        count: int,
        difficulty: Optional[str],
        exclude_terms: List[str],
        feedback_items: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """RAG 검색 → 프롬프트 조립 → LLM 호출 → JSON 파싱."""
        # 1) RAG 검색: 정답 후보
        docs = search_with_filter(query="무역 용어", k=10)
        reference_data = _format_reference_data(docs)

        # 2) RAG 검색: 오답 후보 (유사 용어)
        distractor_docs = search_with_filter(query="무역 용어 유사 개념", k=10)
        distractor_data = _format_reference_data(distractor_docs)

        # 3) 난이도 지시문
        if difficulty:
            difficulty_instruction = f"{count}문제를 모두 {difficulty} 난이도로 출제하세요."
        else:
            if count >= 5:
                difficulty_instruction = f"{count}문제를 easy 2개, medium 2개, hard 1개로 혼합하여 출제하세요."
            else:
                difficulty_instruction = f"{count}문제를 출제하세요. 난이도는 적절히 혼합하세요."

        # 4) 제외 용어 지시문
        if exclude_terms:
            terms_str = ", ".join(exclude_terms)
            exclude_instruction = f"\n- 다음 용어는 이미 사용했으므로 제외하세요: [{terms_str}]"
        else:
            exclude_instruction = ""

        # 5) 피드백 지시문 (재시도 시)
        if feedback_items:
            fb_lines = []
            for fb in feedback_items:
                issues_str = "; ".join(fb.get("issues", []))
                fb_lines.append(f"  - 이전 문제 불합격 사유: {issues_str}")
            feedback_instruction = "\n- 이전 생성에서 아래 문제가 지적되었습니다. 같은 실수를 반복하지 마세요:\n" + "\n".join(fb_lines)
        else:
            feedback_instruction = ""

        # 6) 프롬프트 조립
        prompt = (
            self.system_prompt
            .replace("{reference_data}", reference_data)
            .replace("{distractor_data}", distractor_data)
            .replace("{difficulty_instruction}", difficulty_instruction)
            .replace("{exclude_instruction}", exclude_instruction)
            .replace("{feedback_instruction}", feedback_instruction)
        )

        # 7) LLM 호출
        raw = await call_llm(
            user_message=f"위 조건에 맞는 무역 용어 퀴즈 {count}문제를 JSON 배열로 출제해주세요.",
            system_prompt=prompt,
        )

        # 8) 파싱 & quiz_id 발급
        try:
            quiz_list = _parse_quiz_json(raw)
        except (json.JSONDecodeError, KeyError):
            logger.error(f"퀴즈 JSON 파싱 실패: {raw[:200]}")
            return []

        for q in quiz_list:
            q["quiz_id"] = str(uuid.uuid4())[:8]

        return quiz_list

    # ──────────────────────────────────────────
    # 답안 채점
    # ──────────────────────────────────────────

    @traceable(name="quiz_evaluate_answer", run_type="chain")
    def _evaluate_answer(self, quiz_id: str, user_answer: int) -> Dict[str, Any]:
        """저장된 퀴즈의 정답과 사용자 답안을 비교."""
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

    # ──────────────────────────────────────────
    # 헬퍼
    # ──────────────────────────────────────────

    @staticmethod
    def _split_by_validity(
        quizzes: List[Dict[str, Any]],
        eval_results: List[Dict[str, Any]],
    ) -> tuple:
        """eval 결과를 기반으로 합격/불합격 분리."""
        eval_map = {r["quiz_id"]: r for r in eval_results}
        passed, failed = [], []
        for q in quizzes:
            qid = q["quiz_id"]
            result = eval_map.get(qid, {})
            if result.get("is_valid", False):
                passed.append(q)
            else:
                failed.append(q)
        return passed, failed

    @staticmethod
    def _collect_feedback(
        failed_quizzes: List[Dict[str, Any]],
        eval_results: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """불합격 문제들의 issues를 피드백 목록으로 수집."""
        eval_map = {r["quiz_id"]: r for r in eval_results}
        feedback = []
        for q in failed_quizzes:
            qid = q["quiz_id"]
            result = eval_map.get(qid, {})
            feedback.append({
                "quiz_id": qid,
                "issues": result.get("issues", ["사유 없음"]),
            })
        return feedback

    @staticmethod
    def _extract_term(quiz: Dict[str, Any]) -> str:
        """퀴즈에서 핵심 용어를 추출 (대체 생성 시 제외 목록용)."""
        quiz_type = quiz.get("quiz_type", "")
        if "용어→설명" in quiz_type:
            # 문제가 용어 → 문제 텍스트에서 추출
            return quiz.get("question", "").split("란")[0].split("은")[0].strip().strip('"').strip("'")
        else:
            # 설명→용어 → 정답 선택지가 용어
            correct_idx = quiz.get("answer", 0)
            choices = quiz.get("choices", [])
            return choices[correct_idx] if correct_idx < len(choices) else ""

    def _error_response(self, message: str, difficulty: Optional[str]) -> Dict[str, Any]:
        return {
            "response": {"error": message},
            "agent_type": self.agent_type,
            "metadata": {"difficulty": difficulty},
        }
