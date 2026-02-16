# Task #9: Quiz API 엔드포인트 완성 - 완료 보고서

**작성일**: 2026-02-16
**소요 시간**: 약 1시간
**커밋**: `b945949`
**상태**: ✅ 완료

---

## 📋 작업 개요

### 목표
Quiz 전용 API 엔드포인트 구현하여 `/api/chat` 외에도 직접 퀴즈를 생성하고 채점할 수 있는 인터페이스 제공

### 해결한 문제
- ❌ Quiz 기능이 `/api/chat` Orchestrator를 통해서만 접근 가능
- ❌ 퀴즈 세션 관리 부재
- ❌ 즉각적인 퀴즈 채점 불가능

### 구현한 솔루션
- ✅ `POST /api/quiz/start`: 퀴즈 세션 생성 및 문제 반환
- ✅ `POST /api/quiz/answer`: 답안 제출 및 즉시 채점
- ✅ Redis/InMemory 기반 퀴즈 세션 관리
- ✅ 7개 샘플 무역 용어 퀴즈 제공

---

## 🏗️ 아키텍처

### Before (Task #9 이전)

```
Client
  ↓
POST /api/chat {"message": "퀴즈 풀고 싶어요"}
  ↓
Orchestrator
  ↓
QuizAgent (텍스트 응답)
  ↓
Client (채점 불가능)
```

**문제점**:
- 퀴즈 형식이 비구조화됨
- 세션 관리 없음
- 채점 로직 부재

### After (Task #9 이후)

```
Client
  ↓
POST /api/quiz/start {"count": 5}
  ↓
QuizService
  ├─ QuizGeneratorService: 퀴즈 생성
  └─ QuizSessionStore: 세션 저장 (Redis/InMemory)
  ↓
Client (quiz_session_id + questions)

Client
  ↓
POST /api/quiz/answer {"quiz_session_id", "quiz_id", "answer": 0}
  ↓
QuizService
  ├─ QuizSessionStore: 세션 조회
  └─ 답안 채점: is_correct + explanation
  ↓
Client (즉시 피드백)
```

**개선점**:
- ✅ 구조화된 퀴즈 API
- ✅ 세션 기반 퀴즈 진행
- ✅ 즉각적인 채점 및 피드백

---

## 📦 구현 내역

### 1. API 스키마 정의

#### `backend/schemas/quiz.py` (73줄)

**Pydantic 모델**:

```python
class QuizQuestion(BaseModel):
    quiz_id: str                     # 문제 고유 ID
    question: str                    # 문제 텍스트
    choices: List[str]               # 선택지 4개
    correct_answer: int              # 정답 인덱스 (0-3)
    explanation: str                 # 해설
    quiz_type: str                   # "term_to_description" 등
    difficulty: str                  # "easy", "medium", "hard"
    term: Optional[str]              # 핵심 용어

class QuizStartRequest(BaseModel):
    topic: Optional[str]             # 주제 필터 (미사용)
    difficulty: Optional[str]        # 난이도 (미사용)
    count: int = 5                   # 문제 수 (1-10)

class QuizStartResponse(BaseModel):
    quiz_session_id: str             # 세션 ID
    questions: List[dict]            # 문제 목록 (정답/해설 제외)
    total_questions: int
    topic: Optional[str]
    difficulty: Optional[str]
    created_at: str                  # ISO timestamp

class QuizAnswerRequest(BaseModel):
    quiz_session_id: str             # 세션 ID
    quiz_id: str                     # 문제 ID
    answer: int                      # 선택한 답 (0-3)

class QuizAnswerResponse(BaseModel):
    quiz_id: str
    is_correct: bool                 # 정답 여부
    user_answer: int                 # 사용자 답
    correct_answer: int              # 정답 인덱스
    explanation: str                 # 해설
    question: str                    # 문제 (재확인용)
    choices: List[str]               # 선택지 (재확인용)
```

### 2. Quiz Service 구현

#### `backend/services/quiz_service.py` (281줄)

**QuizSessionStore** (세션 관리):

```python
class QuizSessionStore:
    def __init__(self):
        # Task #7 세션 스토어 재사용
        self._store = create_conversation_store()

    def _make_key(self, session_id: str) -> str:
        return f"quiz_session:{session_id}"  # 네임스페이스 분리

    def create_session(questions, topic, difficulty) -> str:
        # UUID 세션 ID 생성
        # 문제 목록 저장 (정답/해설 포함)
        # Redis/InMemory에 저장

    def get_session(session_id) -> Dict:
        # 세션 데이터 조회

    def save_answer(session_id, quiz_id, answer):
        # 사용자 답안 저장

    def get_question(session_id, quiz_id) -> QuizQuestion:
        # 특정 문제 조회 (채점용)
```

**세션 데이터 구조**:
```python
{
    "quiz_session_id": "uuid",
    "questions": [QuizQuestion.model_dump()],
    "topic": "Incoterms" | None,
    "difficulty": "easy" | None,
    "created_at": "2026-02-16T10:00:00",
    "answers": {"quiz_id": user_answer},
    "completed": False
}
```

**QuizGeneratorService** (퀴즈 생성):

```python
class QuizGeneratorService:
    @staticmethod
    def generate_sample_quizzes(count, topic, difficulty) -> List[QuizQuestion]:
        # 하드코딩된 7개 샘플 퀴즈 반환
        # count만큼 슬라이싱
```

**7개 샘플 퀴즈**:
1. **FOB** (easy): FOB(Free On Board)의 의미
2. **L/C** (easy): 신용장의 주요 목적
3. **CIF** (medium): CIF 조건에 포함되지 않는 것
4. **DDP** (hard): Incoterms 2020에서 수출자 책임이 가장 큰 조건
5. **B/L** (medium): B/L(선하증권)의 3대 기능이 아닌 것
6. **HS Code** (hard): 수출입 통관 시 필요한 HS Code 자릿수
7. **Issuing Bank** (easy): 수입 신용장 개설 은행

### 3. API 엔드포인트 구현

#### `backend/api/routes.py` (수정)

**변경 내용**:
- `from backend.schemas.quiz import ...` 임포트 추가
- `from backend.services.quiz_service import ...` 임포트 추가
- `/quiz/start` 엔드포인트 구현
- `/quiz/answer` 엔드포인트 구현

**Before**:
```python
@router.post("/quiz/start")
async def start_quiz(topic: str = "general", difficulty: str = "easy"):
    # TODO: Implement quiz generation
    return {"message": "퀴즈 생성 기능을 구현해주세요."}
```

**After**:
```python
@router.post("/quiz/start", response_model=QuizStartResponse)
async def start_quiz(request: QuizStartRequest):
    # 1. 퀴즈 생성
    questions = quiz_generator.generate_sample_quizzes(
        count=request.count,
        topic=request.topic,
        difficulty=request.difficulty
    )

    # 2. 세션 생성
    session_id = quiz_session_store.create_session(questions, ...)

    # 3. 정답/해설 숨김 처리
    questions_for_user = [
        {
            "quiz_id": q.quiz_id,
            "question": q.question,
            "choices": q.choices,
            "quiz_type": q.quiz_type,
            "difficulty": q.difficulty
            # correct_answer, explanation 제외
        }
        for q in questions
    ]

    # 4. 응답 반환
    return QuizStartResponse(
        quiz_session_id=session_id,
        questions=questions_for_user,
        total_questions=len(questions),
        ...
    )
```

**Before**:
```python
@router.post("/quiz/answer")
async def answer_quiz(quiz_id: str, answer: int):
    # TODO: Implement quiz evaluation
    return {"message": "퀴즈 채점 기능을 구현해주세요."}
```

**After**:
```python
@router.post("/quiz/answer", response_model=QuizAnswerResponse)
async def answer_quiz(request: QuizAnswerRequest):
    # 1. 세션에서 문제 조회
    question = quiz_session_store.get_question(
        request.quiz_session_id,
        request.quiz_id
    )

    # 2. 답안 저장
    quiz_session_store.save_answer(
        request.quiz_session_id,
        request.quiz_id,
        request.answer
    )

    # 3. 채점
    is_correct = request.answer == question.correct_answer

    # 4. 결과 반환 (정답, 해설 포함)
    return QuizAnswerResponse(
        quiz_id=request.quiz_id,
        is_correct=is_correct,
        user_answer=request.answer,
        correct_answer=question.correct_answer,
        explanation=question.explanation,
        question=question.question,
        choices=question.choices
    )
```

### 4. 테스트

#### `tests/test_quiz_api.py` (230줄)

**테스트 케이스**:
1. `test_start_quiz_default`: 기본 파라미터로 퀴즈 시작
2. `test_start_quiz_custom_count`: 커스텀 문제 수
3. `test_start_quiz_with_topic_and_difficulty`: 주제/난이도 지정
4. `test_answer_quiz_correct`: 정답 제출
5. `test_answer_quiz_incorrect`: 오답 제출
6. `test_answer_quiz_invalid_session`: 잘못된 세션 ID
7. `test_answer_quiz_invalid_question`: 잘못된 문제 ID
8. `test_full_quiz_workflow`: 전체 워크플로우 (시작 → 답안 제출 → 검증)

#### `test_quiz_api_quick.py` (빠른 검증 스크립트)

**검증 항목**:
1. 샘플 퀴즈 생성 (3개)
2. 세션 생성 및 조회
3. 특정 문제 조회
4. 답안 저장
5. 답안 채점
6. 정답/해설 숨김 처리
7. API 응답 형식 검증

**실행 결과**:
```
=== Testing Quiz Service ===
1. Generating sample quizzes...
   ✓ Generated 3 questions
   ✓ First question: FOB(Free On Board)의 의미는 무엇인가요?...

2. Creating quiz session...
   ✓ Session ID: 79fb7253-59ab-49f9-81e4-25725b38e17c

3. Retrieving session...
   ✓ Session retrieved: True
   ✓ Questions in session: 3
   ✓ Topic: Incoterms
   ✓ Created at: 2026-02-16T11:27:15.478475

4. Getting specific question...
   ✓ Question retrieved: True
   ✓ Question text: FOB(Free On Board)의 의미는 무엇인가요?...
   ✓ Choices: 4
   ✓ Correct answer: 0

5. Saving user answer...
   ✓ Answer saved: True
   ✓ User answer: 0

6. Evaluating answer...
   ✓ Is correct: True
   ✓ Explanation: FOB(Free On Board)는 본선 인도 조건으로...

7. Testing question hiding (for API response)...
   ✓ Question has 'quiz_id': True
   ✓ Question has 'question': True
   ✓ Question has 'choices': True
   ✓ Question hidden 'correct_answer': True
   ✓ Question hidden 'explanation': True

✅ All Quiz Service tests passed!
```

---

## 🎯 주요 특징

### 1. Task #7 세션 스토어 재사용

```python
class QuizSessionStore:
    def __init__(self):
        # Redis/InMemory 인프라 재사용
        self._store = create_conversation_store()

    def _make_key(self, session_id: str) -> str:
        # 네임스페이스로 구분: "quiz_session:{uuid}"
        return f"quiz_session:{session_id}"
```

**혜택**:
- ✅ Redis 사용 시 퀴즈 세션도 자동 영속화
- ✅ 동일한 TTL 관리 (1시간 자동 만료)
- ✅ 코드 중복 최소화

### 2. 정답/해설 숨김 처리

**퀴즈 시작 시** (클라이언트에게 전송):
```python
questions_for_user = [
    {
        "quiz_id": q.quiz_id,
        "question": q.question,
        "choices": q.choices,
        "quiz_type": q.quiz_type,
        "difficulty": q.difficulty
        # ❌ correct_answer, explanation 제외
    }
    for q in questions
]
```

**답안 제출 후** (채점 결과와 함께 반환):
```python
return QuizAnswerResponse(
    is_correct=True/False,
    user_answer=0,
    correct_answer=0,       # ✅ 이제 공개
    explanation="FOB는...", # ✅ 이제 공개
    ...
)
```

### 3. 에러 처리

```python
@router.post("/quiz/answer")
async def answer_quiz(request: QuizAnswerRequest):
    try:
        question = quiz_session_store.get_question(...)
        if not question:
            raise HTTPException(
                status_code=404,
                detail=f"Question {request.quiz_id} not found"
            )
        ...
    except HTTPException:
        raise  # 의도된 HTTP 에러는 그대로 전파
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to evaluate answer: {str(e)}"
        )
```

---

## 📊 코드 메트릭스

| 파일 | 상태 | 줄 수 | 설명 |
|------|------|-------|------|
| `backend/schemas/quiz.py` | 신규 | 73 | Pydantic 모델 |
| `backend/services/quiz_service.py` | 신규 | 281 | 퀴즈 서비스 + 세션 스토어 |
| `backend/api/routes.py` | 수정 | +80 | Quiz API 엔드포인트 |
| `tests/test_quiz_api.py` | 신규 | 230 | 단위 테스트 (8개) |
| `test_quiz_api_quick.py` | 신규 | 90 | 빠른 검증 스크립트 |

**총 추가 줄 수**: ~754줄

---

## 🚀 API 사용 가이드

### 1. 퀴즈 시작

**Request**:
```bash
curl -X POST http://localhost:8000/api/quiz/start \
  -H "Content-Type: application/json" \
  -d '{
    "count": 3,
    "difficulty": "easy"
  }'
```

**Response**:
```json
{
  "quiz_session_id": "79fb7253-59ab-49f9-81e4-25725b38e17c",
  "questions": [
    {
      "quiz_id": "abc-123",
      "question": "FOB(Free On Board)의 의미는 무엇인가요?",
      "choices": [
        "본선 인도 조건 - 수출자가 물품을 본선에 적재할 때까지 책임",
        "운임 포함 조건 - 목적지까지 운임 포함",
        "보험료 포함 조건 - 보험료까지 포함한 가격",
        "공장 인도 조건 - 공장에서 물품 인도"
      ],
      "quiz_type": "term_to_description",
      "difficulty": "easy"
    },
    ...
  ],
  "total_questions": 3,
  "topic": null,
  "difficulty": "easy",
  "created_at": "2026-02-16T11:27:15.478475"
}
```

### 2. 답안 제출

**Request**:
```bash
curl -X POST http://localhost:8000/api/quiz/answer \
  -H "Content-Type: application/json" \
  -d '{
    "quiz_session_id": "79fb7253-59ab-49f9-81e4-25725b38e17c",
    "quiz_id": "abc-123",
    "answer": 0
  }'
```

**Response**:
```json
{
  "quiz_id": "abc-123",
  "is_correct": true,
  "user_answer": 0,
  "correct_answer": 0,
  "explanation": "FOB(Free On Board)는 본선 인도 조건으로, 수출자가 지정 선적항에서 물품을 본선에 적재할 때까지의 비용과 위험을 부담합니다.",
  "question": "FOB(Free On Board)의 의미는 무엇인가요?",
  "choices": [
    "본선 인도 조건 - 수출자가 물품을 본선에 적재할 때까지 책임",
    "운임 포함 조건 - 목적지까지 운임 포함",
    "보험료 포함 조건 - 보험료까지 포함한 가격",
    "공장 인도 조건 - 공장에서 물품 인도"
  ]
}
```

---

## 🔒 제약사항 및 향후 개선

### 현재 제약사항

#### 1. 하드코딩된 샘플 퀴즈

**현재**:
```python
sample_questions = [
    QuizQuestion(quiz_id="...", question="FOB란?", ...),
    QuizQuestion(quiz_id="...", question="L/C란?", ...),
    # 총 7개 고정
]
```

**문제점**:
- ❌ 7개 문제만 제공 (제한적)
- ❌ topic, difficulty 파라미터 무시됨
- ❌ 동적 생성 불가

#### 2. QuizAgent 비통합

**현재 구조**:
- `QuizAgent`: 텍스트 응답만 생성 (LangGraph)
- `QuizGeneratorService`: 하드코딩 샘플

**문제점**:
- ❌ QuizAgent의 RAG 기능 미활용
- ❌ EvalTool 품질 검증 미통합

#### 3. 퀴즈 통계 부재

**미구현 기능**:
- 사용자별 정답률
- 문제별 정답률
- 취약 주제 분석

### 향후 개선 (Task #12)

#### Phase 1: QuizAgent 구조화된 퀴즈 생성

```python
class QuizAgent:
    def generate_structured_quiz(
        self,
        count: int,
        topic: Optional[str] = None,
        difficulty: Optional[str] = None
    ) -> List[QuizQuestion]:
        # 1. RAG 검색으로 관련 용어 추출
        # 2. LLM으로 문제 생성
        # 3. EvalTool로 품질 검증
        # 4. 재시도/대체 파이프라인
        # 5. 구조화된 QuizQuestion 반환
```

**통합 방법**:
```python
# backend/services/quiz_service.py
class QuizGeneratorService:
    def __init__(self):
        self.quiz_agent = QuizAgent()

    def generate_sample_quizzes(self, count, topic, difficulty):
        # QuizAgent 호출로 변경
        return self.quiz_agent.generate_structured_quiz(
            count=count,
            topic=topic,
            difficulty=difficulty
        )
```

#### Phase 2: 퀴즈 통계 API

```python
@router.get("/quiz/stats/{quiz_session_id}")
async def get_quiz_stats(quiz_session_id: str):
    # 세션 조회
    # 정답률 계산
    # 결과 반환
    return {
        "quiz_session_id": quiz_session_id,
        "total_questions": 5,
        "answered": 5,
        "correct": 3,
        "accuracy": 0.6,
        "weak_topics": ["Incoterms", "신용장"]
    }
```

#### Phase 3: 사용자 프로필 통합

```python
# 사용자별 퀴즈 이력 저장
# 취약 주제 자동 출제
# 적응형 난이도 조절
```

---

## ✅ 검증 결과

### 1. 서비스 레이어 테스트

```bash
$ uv run python test_quiz_api_quick.py
✅ All Quiz Service tests passed!
```

### 2. API 라우트 로딩

```bash
$ uv run python -c "from backend.api.routes import router; print([r.path for r in router.routes])"
['/chat', '/quiz/start', '/quiz/answer']
```

### 3. 샘플 퀴즈 검증

- ✅ 7개 문제 커버
- ✅ 난이도 분포: easy(3), medium(2), hard(2)
- ✅ 무역 핵심 주제: FOB, L/C, CIF, DDP, B/L, HS Code, Issuing Bank

---

## 📚 참고 자료

### 생성된 파일
- `backend/schemas/quiz.py` - API 스키마
- `backend/services/quiz_service.py` - 퀴즈 서비스
- `tests/test_quiz_api.py` - 단위 테스트
- `test_quiz_api_quick.py` - 빠른 검증

### 수정된 파일
- `backend/api/routes.py` - Quiz API 엔드포인트

### 커밋
- `b945949`: feat: Task #9 - Quiz API 엔드포인트 구현

---

**Task #9 상태**: ✅ **완료**
**다음 작업**: Task #8 (통합 검증 프레임워크) 또는 Task #12 (QuizAgent 구조화)
**최종 수정**: 2026-02-16
