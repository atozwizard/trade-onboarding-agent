"""
퀴즈 학습 에이전트 (RAG 기반)

[전체 흐름]
  사용자 요청 → routes.py → QuizAgent.run()
    ├─ action="generate" → RAG 검색 → LLM 퀴즈 생성 → 저장 후 반환
    └─ action="evaluate" → 저장된 퀴즈에서 정답 비교 → 결과 반환

[이전 방식과 차이]
  - 이전: dataset/ 폴더의 JSON 파일을 직접 읽어서 퀴즈 소스로 사용
  - 현재: ChromaDB 벡터 DB에서 RAG 검색으로 관련 데이터를 가져와 퀴즈 소스로 사용
"""
import json
import uuid
import os
from typing import Dict, Any, Optional

# call_llm: Upstage Solar LLM에 프롬프트를 보내고 응답 텍스트를 받는 함수
from backend.utils.llm import call_llm
# search_with_filter: ChromaDB에서 메타데이터 필터 조건으로 유사 문서를 검색하는 함수
from backend.rag.retriever import search_with_filter

# ──────────────────────────────────────────────
# 상수 정의
# ──────────────────────────────────────────────

# 프롬프트 파일이 위치한 디렉토리 경로
# 이 파일(quiz_agent.py) 기준으로 ../prompts/ 를 가리킴
PROMPTS_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), '..', 'prompts'
)

# 주제(topic)별 RAG 검색 시 사용할 메타데이터 필터 매핑
# 예: topic="mistakes" → ChromaDB에서 document_type="common_mistake"인 문서만 검색
# "general"은 필터 없이 전체 문서에서 검색
TOPIC_FILTER_MAP: Dict[str, Dict[str, Optional[str]]] = {
    "general": {},                                        # 필터 없음 (전체 검색)
    "mistakes": {"document_type": "common_mistake"},      # 자주 하는 실수 관련 문서
    "negotiation": {"document_type": "negotiation_strategy"},  # 협상 전략 문서
    "country": {"document_type": "country_guideline"},    # 국가별 가이드라인 문서
    "documents": {"document_type": "error_checklist"},    # 서류 오류 체크리스트 문서
}

# 사용자가 선택한 난이도(easy/medium/hard)를
# ChromaDB 메타데이터의 level 값(beginner/working/manager)으로 변환
DIFFICULTY_LEVEL_MAP: Dict[str, str] = {
    "easy": "beginner",   # 신입 수준
    "medium": "working",  # 실무자 수준
    "hard": "manager",    # 관리자 수준
}

# 생성된 퀴즈를 메모리에 임시 저장하는 딕셔너리
# key: quiz_id (8자리 UUID), value: 퀴즈 데이터 (question, choices, answer, explanation)
# 서버가 재시작되면 초기화됨 (영구 저장이 아님)
_quiz_store: Dict[str, Dict[str, Any]] = {}


# ──────────────────────────────────────────────
# 유틸리티 함수
# ──────────────────────────────────────────────

def _load_prompt(filename: str) -> str:
    """프롬프트 템플릿 파일(.txt)을 읽어서 문자열로 반환한다.
    반환된 문자열에는 {reference_data}, {topic}, {difficulty} 같은
    플레이스홀더가 포함되어 있고, 나중에 .replace()로 실제 값을 채운다.
    """
    prompt_path = os.path.join(PROMPTS_DIR, filename)
    with open(prompt_path, "r", encoding="utf-8") as f:
        return f.read()


def _parse_quiz_json(raw: str) -> Dict[str, Any]:
    """LLM이 반환한 텍스트에서 JSON을 추출하여 파싱한다.
    LLM이 ```json ... ``` 코드블록으로 감쌀 수 있으므로 이를 제거한 후 파싱한다.

    예시 입력:
        ```json
        {"question": "...", "choices": [...], "answer": 0, "explanation": "..."}
        ```
    → {"question": "...", "choices": [...], "answer": 0, "explanation": "..."} (dict)
    """
    text = raw.strip()
    # ```json 또는 ``` 으로 시작하는 줄 제거
    if text.startswith("```"):
        lines = text.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines)
    return json.loads(text)


def _format_reference_data(docs: list) -> str:
    """RAG 검색 결과(문서 리스트)를 LLM에게 넘길 텍스트 형태로 변환한다.

    입력 예시 (docs):
        [{"document": "FOB는 ...", "metadata": {"topic": "incoterms", "level": "beginner"}, "distance": 0.3}]

    출력 예시:
        - FOB는 ... (topic: incoterms | level: beginner)
    """
    if not docs:
        return "(참고 데이터 없음)"
    lines = []
    for doc in docs:
        content = doc.get("document", "")
        metadata = doc.get("metadata", {})
        if metadata:
            # 메타데이터를 "key: value | key: value" 형태로 합침
            detail = " | ".join(
                f"{k}: {v}" for k, v in metadata.items() if v
            )
            lines.append(f"- {content} ({detail})" if detail else f"- {content}")
        else:
            lines.append(f"- {content}")
    return "\n".join(lines)


# ──────────────────────────────────────────────
# QuizAgent 클래스
# ──────────────────────────────────────────────

class QuizAgent:
    """RAG 기반 퀴즈 학습 에이전트

    routes.py에서 싱글톤으로 생성되어 사용된다:
        quiz_agent = QuizAgent()
        result = await quiz_agent.run("퀴즈 생성", {"action": "generate", "topic": "general", "difficulty": "easy"})
    """

    agent_type: str = "quiz"

    def __init__(self):
        # 서버 시작 시 프롬프트 템플릿을 한 번만 파일에서 읽어 메모리에 보관
        self.system_prompt = _load_prompt("quiz_prompt.txt")

    async def run(self, user_input: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """에이전트 진입점. context["action"] 값에 따라 분기한다.

        - "generate": 새 퀴즈를 생성 (RAG + LLM)
        - "evaluate": 이미 생성된 퀴즈에 대해 사용자 답안을 채점
        """
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
        """RAG 검색 → 프롬프트 조립 → LLM 호출 → JSON 파싱 → 저장 순서로 퀴즈를 생성한다.

        전체 파이프라인:
            1) topic/difficulty → ChromaDB 필터 조건 구성
            2) ChromaDB에서 유사 문서 5개 검색
            3) 검색 결과를 텍스트로 변환
            4) quiz_prompt.txt 템플릿에 검색 결과 + topic + difficulty 삽입
            5) LLM에 프롬프트 전송 → 퀴즈 JSON 응답 수신
            6) JSON 파싱 후 quiz_id 발급, 메모리에 저장
        """
        # 1) RAG 필터 구성
        #    예: topic="mistakes", difficulty="easy"
        #    → filters = {"document_type": "common_mistake", "level": "beginner"}
        filters = TOPIC_FILTER_MAP.get(topic, {}).copy()
        level = DIFFICULTY_LEVEL_MAP.get(difficulty, "beginner")
        filters["level"] = level

        # 2) ChromaDB에서 필터 조건에 맞는 유사 문서 5개 검색
        query = f"{topic} 무역 퀴즈 {difficulty}"
        docs = search_with_filter(query=query, k=5, **filters)

        # 3) 검색된 문서들을 프롬프트에 삽입할 텍스트로 변환
        reference_data = _format_reference_data(docs)

        # 4) 프롬프트 템플릿의 플레이스홀더를 실제 값으로 교체
        #    {reference_data} → 검색 결과 텍스트
        #    {topic} → "general" 등
        #    {difficulty} → "easy" 등
        prompt = (
            self.system_prompt
            .replace("{reference_data}", reference_data)
            .replace("{topic}", topic)
            .replace("{difficulty}", difficulty)
        )

        # 5) Upstage Solar LLM 호출
        raw_response = await call_llm(
            user_message="위 조건에 맞는 무역 퀴즈 1문제를 JSON으로 출제해주세요.",
            system_prompt=prompt,
        )

        # 6) LLM 응답에서 JSON 파싱
        #    실패 시 에러 응답 반환 (LLM이 JSON 형식을 지키지 않은 경우)
        try:
            quiz_data = _parse_quiz_json(raw_response)
        except (json.JSONDecodeError, KeyError):
            return {
                "response": {"error": "퀴즈 생성에 실패했습니다. 다시 시도해주세요."},
                "agent_type": self.agent_type,
                "metadata": {"topic": topic, "difficulty": difficulty, "raw": raw_response},
            }

        # 7) 퀴즈에 고유 ID를 부여하고 메모리에 저장 (나중에 채점할 때 조회용)
        quiz_id = str(uuid.uuid4())[:8]
        _quiz_store[quiz_id] = quiz_data

        # 사용자에게는 quiz_id, 문제, 보기만 반환 (정답/해설은 숨김)
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
        """사용자가 제출한 답안을 저장된 퀴즈의 정답과 비교하여 채점한다.

        Args:
            quiz_id: _generate_quiz()에서 발급한 퀴즈 ID
            user_answer: 사용자가 선택한 보기 인덱스 (0~3)

        Returns:
            정답 여부, 정답 보기, 해설이 포함된 딕셔너리
        """
        # 메모리에서 퀴즈 데이터 조회
        quiz_data = _quiz_store.get(quiz_id)

        if not quiz_data:
            return {
                "response": {"error": f"퀴즈 ID '{quiz_id}'를 찾을 수 없습니다."},
                "agent_type": self.agent_type,
                "metadata": {"quiz_id": quiz_id},
            }

        # 정답 비교 (둘 다 0~3 인덱스)
        correct_answer = quiz_data["answer"]
        is_correct = user_answer == correct_answer

        return {
            "response": {
                "quiz_id": quiz_id,
                "is_correct": is_correct,
                "user_answer": user_answer,
                "correct_answer": correct_answer,
                "correct_choice": quiz_data["choices"][correct_answer],  # 정답 텍스트
                "explanation": quiz_data["explanation"],                 # LLM이 생성한 해설
            },
            "agent_type": self.agent_type,
            "metadata": {"quiz_id": quiz_id},
        }
