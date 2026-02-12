# Quiz Agent & Eval Agent 기획서

## 1. 개요

무역·물류 신입사원 교육을 위한 두 가지 AI 에이전트.

| 에이전트 | 역할 |
|---------|------|
| **QuizAgent** | RAG 검색 기반으로 4지선다 퀴즈 5문제를 생성하고, 사용자 답안을 채점 |
| **EvalAgent** | QuizAgent가 만든 퀴즈의 품질(사실 정확도, 교육 적합도, 실무 팁)을 자동 검증 |

**기술 스택:** FastAPI + ChromaDB(RAG) + Upstage Solar LLM + LangChain

---

## 2. QuizAgent — 퀴즈 생성 및 채점

### 2.1 핵심 기능

#### 기능 A: 퀴즈 생성 (generate)

| 항목 | 내용 |
|------|------|
| **Input** | `topic` (주제), `difficulty` (난이도, Optional) |
| **Output** | 5문제 배열 — 각 문제에 `quiz_id`, `question`, `choices`, `difficulty` 포함 |
| **RAG 검색** | ChromaDB에서 topic별 `document_type` 필터 + difficulty별 `level` 필터로 유사 문서 10건 검색 |
| **LLM** | Upstage Solar (temperature=0.7), 1회 호출로 5문제 JSON 배열 생성 |

**난이도 처리 로직:**
- difficulty 지정 시 → 5문제 모두 해당 난이도로 생성
- difficulty 미지정 시 → easy 2개 + medium 2개 + hard 1개 혼합 구성

**RAG 필터 매핑:**

| topic | ChromaDB document_type 필터 |
|-------|---------------------------|
| general | (필터 없음 — 전체 문서 검색) |
| mistakes | `common_mistake` |
| negotiation | `negotiation_strategy` |
| country | `country_guideline` |
| documents | `error_checklist` |

| difficulty | ChromaDB level 필터 |
|------------|-------------------|
| easy | `beginner` |
| medium | `working` |
| hard | `manager` |
| 미지정 | (level 필터 없음) |

#### 기능 B: 답안 채점 (evaluate)

| 항목 | 내용 |
|------|------|
| **Input** | `quiz_id`, `answer` (0~3 인덱스) |
| **Output** | `is_correct`, `correct_answer`, `correct_choice`, `explanation` |
| **RAG 검색** | 없음 (메모리 저장된 데이터로 비교) |
| **LLM** | 없음 (단순 인덱스 비교) |

### 2.2 퀴즈 생성 파이프라인

```
사용자 요청 (topic, difficulty)
    │
    ▼
① TOPIC_FILTER_MAP에서 document_type 필터 조회
   difficulty가 있으면 DIFFICULTY_LEVEL_MAP에서 level 필터 추가
    │
    ▼
② ChromaDB search_with_filter(query, k=10, **filters)
   → 유사 문서 10건 검색
    │
    ▼
③ _format_reference_data()
   → 검색 결과를 "- 내용 (메타데이터)" 텍스트로 변환
    │
    ▼
④ quiz_prompt.txt 템플릿에 플레이스홀더 삽입
   {reference_data} → 검색 결과 텍스트
   {topic} → 주제
   {difficulty_instruction} → "모두 easy 난이도로" 또는 "easy 2, medium 2, hard 1 혼합"
    │
    ▼
⑤ call_llm() → Upstage Solar에 프롬프트 전송
   → 5문제 JSON 배열 수신
    │
    ▼
⑥ _parse_quiz_json() → JSON 파싱 (코드블록 제거 포함)
   → 단일 객체도 배열로 감싸기
    │
    ▼
⑦ 각 문제에 quiz_id(8자리 UUID) 발급 → _quiz_store에 저장
   → 사용자에게는 정답/해설 숨기고 quiz_id + question + choices만 반환
```

### 2.3 LLM 응답 포맷 (quiz_prompt.txt가 요구하는 형식)

```json
[
  {
    "question": "상황 설명 및 질문",
    "choices": ["보기1", "보기2", "보기3", "보기4"],
    "answer": 0,
    "explanation": "정답 해설",
    "difficulty": "easy"
  },
  ...
]
```

- `answer`: 정답 보기의 인덱스 (0~3)
- `difficulty`: 해당 문제의 난이도 (easy / medium / hard)

---

## 3. EvalAgent — 퀴즈 품질 평가

### 3.1 핵심 기능

| 항목 | 내용 |
|------|------|
| **Input** | `quiz_id` (평가 대상 퀴즈), `topic` (원본 대조용) |
| **Output** | `grounding_score`, `educational_score`, `insight_score`, `is_passed`, `feedback` |
| **RAG 검색** | 퀴즈 question 텍스트로 ChromaDB 검색 (필터 없이 유사도 기반, 5건) |
| **LLM** | Upstage Solar (temperature=0.3 — 일관된 평가를 위해 낮은 온도) |

### 3.2 평가 기준 (3축 채점)

| 점수 | 기준 | 만점 조건 |
|------|------|----------|
| **grounding_score** (0~10) | 원본 데이터 일치도 | 사실, 숫자, 용어, 날짜 100% 정확 |
| **educational_score** (0~10) | 교육 적합도 | 신입사원 이해 가능 + 실무 적용 가능 |
| **insight_score** (0~10) | 실무 팁 품질 | "실무에서는~", "주의할 점은~" 등 구체적 조언 포함 |

### 3.3 통과/불합격 판정 알고리즘 (`_validate_eval_result`)

```python
# 1) 점수 클램핑 (LLM이 범위 벗어난 값 줄 수 있으므로)
gs  = clamp(grounding_score, 0, 10)
es  = clamp(educational_score, 0, 10)
ins = clamp(insight_score, 0, 10)

# 2) 통과 조건: 두 가지 모두 만족해야 pass
total_ratio = (gs + es + ins) / 30
is_passed = (total_ratio >= 0.8) AND (gs == 10)
```

**핵심:** grounding(사실 정확도)이 만점이 아니면 나머지 점수가 아무리 높아도 불합격.
LLM이 반환한 `is_passed`는 신뢰하지 않고, 서버에서 재계산한다.

### 3.4 퀴즈 평가 파이프라인

```
사용자 요청 (quiz_id, topic)
    │
    ▼
① routes.py에서 _quiz_store[quiz_id] 조회 → quiz_data 확보
    │
    ▼
② quiz_data["question"]을 검색어로 ChromaDB 검색
   → search_with_filter(query=question, k=5) — 필터 없이 유사도 검색
   → 퀴즈와 관련된 원본 문서 5건 확보
    │
    ▼
③ _format_reference_data() → 원본 문서를 텍스트로 변환
    │
    ▼
④ eval_prompt.txt 템플릿에 플레이스홀더 삽입
   {quiz_data} → 퀴즈 JSON 문자열
   {reference_data} → 원본 문서 텍스트
    │
    ▼
⑤ call_llm(temperature=0.3) → 낮은 온도로 일관된 평가 유도
   → 평가 결과 JSON 수신
    │
    ▼
⑥ _parse_eval_json() → JSON 파싱
    │
    ▼
⑦ _validate_eval_result() → 점수 0~10 클램핑 + is_passed 서버측 재계산
   → 평가 리포트 반환
```

---

## 4. 생성된 파일 목록

### 에이전트 코드

| 파일 | 역할 |
|------|------|
| `backend/agents/quiz_agent.py` | QuizAgent 클래스 — 퀴즈 생성(RAG+LLM) 및 채점 |
| `backend/agents/eval_agent.py` | EvalAgent 클래스 — 퀴즈 품질 평가(RAG+LLM) |

### 프롬프트 템플릿

| 파일 | 역할 |
|------|------|
| `backend/prompts/quiz_prompt.txt` | 퀴즈 생성용 LLM 프롬프트 (5문제 JSON 배열 출력 지시) |
| `backend/prompts/eval_prompt.txt` | 퀴즈 평가용 LLM 프롬프트 (3축 채점 + JSON 출력 지시) |

### 공통 유틸리티

| 파일 | 역할 |
|------|------|
| `backend/utils/__init__.py` | 패키지 초기화 |
| `backend/utils/llm.py` | `get_llm()` (캐싱된 LLM 인스턴스) + `call_llm()` (비동기 LLM 호출) |

### API 라우트

| 파일 | 역할 |
|------|------|
| `backend/api/routes.py` | 3개 엔드포인트 정의 — `/quiz/start`, `/quiz/answer`, `/quiz/evaluate` |

### RAG 인프라 (기존 유지)

| 파일 | 역할 |
|------|------|
| `backend/rag/retriever.py` | `search()`, `search_with_filter()` — ChromaDB 벡터 검색 |
| `backend/rag/chroma_client.py` | ChromaDB 클라이언트 및 컬렉션 관리 |
| `backend/rag/embedder.py` | Upstage 임베딩 API 호출 |
| `backend/rag/ingest.py` | dataset/ JSON → ChromaDB 임베딩 업로드 |
| `backend/rag/schema.py` | 메타데이터 스키마 정규화 |

---

## 5. 사용 방법 (API 호출)

### 5.1 퀴즈 생성

```bash
# 난이도 지정 — 5문제 모두 easy
curl -X POST http://localhost:8000/api/quiz/start \
  -H "Content-Type: application/json" \
  -d '{"topic": "general", "difficulty": "easy"}'

# 난이도 미지정 — easy 2 + medium 2 + hard 1 혼합
curl -X POST http://localhost:8000/api/quiz/start \
  -H "Content-Type: application/json" \
  -d '{"topic": "mistakes"}'
```

**응답 예시:**
```json
{
  "response": [
    {
      "quiz_id": "a1b2c3d4",
      "question": "FOB 조건에서 운송 보험료를 부담하는 주체는?",
      "choices": ["수출자", "수입자", "포워더", "선사"],
      "difficulty": "easy"
    },
    {
      "quiz_id": "e5f6g7h8",
      "question": "...",
      "choices": ["...", "...", "...", "..."],
      "difficulty": "medium"
    }
  ],
  "agent_type": "quiz",
  "metadata": {"topic": "general", "difficulty": null, "count": 5}
}
```

### 5.2 답안 채점

```bash
curl -X POST http://localhost:8000/api/quiz/answer \
  -H "Content-Type: application/json" \
  -d '{"quiz_id": "a1b2c3d4", "answer": 1}'
```

**응답 예시:**
```json
{
  "response": {
    "quiz_id": "a1b2c3d4",
    "is_correct": true,
    "user_answer": 1,
    "correct_answer": 1,
    "correct_choice": "수입자",
    "explanation": "FOB 조건에서 수입자가 운송 보험료를 부담합니다..."
  },
  "agent_type": "quiz",
  "metadata": {"quiz_id": "a1b2c3d4"}
}
```

### 5.3 퀴즈 품질 평가

```bash
curl -X POST http://localhost:8000/api/quiz/evaluate \
  -H "Content-Type: application/json" \
  -d '{"quiz_id": "a1b2c3d4", "topic": "general"}'
```

**응답 예시:**
```json
{
  "response": {
    "grounding_score": 10,
    "educational_score": 9,
    "insight_score": 8,
    "is_passed": true,
    "feedback": "원본 데이터와 100% 일치하며, 실무 팁이 구체적으로 포함되어 있습니다."
  },
  "agent_type": "eval",
  "metadata": {"topic": "general"}
}
```

### 5.4 코드에서 직접 호출

```python
from backend.agents.quiz_agent import QuizAgent
from backend.agents.eval_agent import EvalAgent

quiz_agent = QuizAgent()
eval_agent = EvalAgent()

# 퀴즈 생성
result = await quiz_agent.run("퀴즈 생성", {
    "action": "generate",
    "topic": "general",
    "difficulty": "easy"       # 생략하면 혼합 출제
})

# 답안 채점
result = await quiz_agent.run("답변 제출", {
    "action": "evaluate",
    "quiz_id": "a1b2c3d4",
    "user_answer": 1
})

# 퀴즈 품질 평가
result = await eval_agent.run("퀴즈 평가", {
    "quiz_data": {"question": "...", "choices": [...], "answer": 0, "explanation": "..."},
    "topic": "general"
})
```

---

## 6. 핵심 로직 요약

### 데이터 저장 구조 (`_quiz_store`)

```
_quiz_store = {
    "a1b2c3d4": {
        "question": "FOB 조건에서...",
        "choices": ["수출자", "수입자", "포워더", "선사"],
        "answer": 1,
        "explanation": "FOB 조건에서 수입자가...",
        "difficulty": "easy"
    },
    "e5f6g7h8": { ... },
    ...
}
```

- 서버 메모리에 저장 (서버 재시작 시 초기화)
- 퀴즈 생성 시 quiz_id별로 개별 저장 → 채점/평가 시 quiz_id로 조회

### 프롬프트 플레이스홀더 치환 흐름

```
quiz_prompt.txt                         eval_prompt.txt
┌─────────────────────┐                 ┌─────────────────────┐
│ {reference_data}    │ ← RAG 검색결과   │ {quiz_data}         │ ← 퀴즈 JSON
│ {topic}             │ ← 주제          │ {reference_data}    │ ← RAG 검색결과
│ {difficulty_instruction} │ ← 난이도지시 └─────────────────────┘
└─────────────────────┘
         ↓                                        ↓
    call_llm()                               call_llm()
    temperature=0.7                          temperature=0.3
         ↓                                        ↓
   5문제 JSON 배열                          평가 JSON 객체
```

### LLM temperature 사용 전략

| 용도 | temperature | 이유 |
|------|------------|------|
| 퀴즈 생성 | 0.7 (기본) | 다양하고 창의적인 문제 출제 필요 |
| 퀴즈 평가 | 0.3 | 일관되고 엄격한 채점 필요 |
