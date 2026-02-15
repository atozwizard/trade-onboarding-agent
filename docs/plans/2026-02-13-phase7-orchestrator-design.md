# Phase 7 설계: Orchestrator + LangGraph State (3-Agent 시스템)

**작성일**: 2026-02-13
**버전**: Phase 7 Design v1.0
**접근법**: 하이브리드 (기존 EmailAgent 재사용 + LangGraph 추가)

---

## 📌 설계 개요

### 목적
기존 EmailAgent를 유지하면서 상위에 LangGraph 기반 Orchestrator를 추가하여 3개 에이전트(Email Coach, Quiz, Risk Detection)를 통합 운영하는 시스템 구축

### 핵심 원칙
- **80% 코드 재사용**: 기존 `backend/agents/email/` 전체 유지
- **EmailAgent 수정 없음**: LangGraph 노드로 래핑만
- **확장성 확보**: Quiz/Risk Detection 에이전트는 stub 노드 생성 후 향후 구현

---

## 🏗️ 아키텍처

### 시스템 구조
```
[사용자 입력]
    ↓
[Orchestrator - LangGraph Workflow]
    ├─ classify_intent (node) - 5가지 의도 분류
    ├─ conditional_routing - 의도별 에이전트 라우팅
    ├─ email_agent_node (기존 EmailAgent 래핑)
    ├─ quiz_agent_node (준비, 미구현)
    ├─ risk_detect_node (준비, 미구현)
    ├─ general_chat_node (간단한 응답)
    └─ format_response (공통 포맷팅)
    ↓
[AgentResponse 반환]
```

### 에이전트 역할 분담

| 에이전트 | 역할 | 상태 |
|----------|------|------|
| **Email Coach** | 이메일 초안 작성 + 검토 (리스크 탐지, 톤 분석, 무역 용어 검증, 단위 검증) | ✅ Phase 6 완료 |
| **Quiz** | 무역 용어·프로세스 퀴즈 학습 | 🔲 Stub 준비 |
| **Risk Detection** | 업무 상황별 예상 실수 TOP 3 + 예방 체크리스트 | 🔲 Stub 준비 |

---

## 🔧 State 정의

### AgentState (TypedDict)

```python
from typing import TypedDict, Literal, Optional, Dict, Any

class AgentState(TypedDict):
    """Orchestrator State"""
    user_input: str  # 사용자 원본 입력
    intent: Literal["quiz", "email_coach", "risk_detect", "general_chat", "out_of_scope"]
    context: Dict[str, Any]  # 세션 컨텍스트 (이전 대화, 사용자 프로필 등)
    response: str  # 최종 응답 텍스트
    metadata: Dict[str, Any]  # 에이전트별 메타데이터 (점수, 리스크 등)
    error: Optional[str]  # 에러 메시지 (있을 경우)
```

**특징**:
- **중간 복잡도**: 필수 필드만 포함, 과도한 상태 관리 배제
- **5가지 intent**: quiz, email_coach, risk_detect, general_chat, out_of_scope
- **error 필드**: 폴백 처리를 위한 에러 추적

---

## 📂 파일 구조

### 신규 생성 파일

```
backend/agents/
├── orchestrator.py (신규) - LangGraph Workflow 정의
├── intent_classifier.py (신규) - LLM 기반 의도 분류
└── email/ (기존 유지)
    ├── email_agent.py
    ├── review_service.py
    ├── trade_term_validator.py
    ├── unit_validator.py
    └── ...

backend/prompts/
└── intent_classification_prompt.txt (신규) - 의도 분류 Few-shot 프롬프트
```

### 수정 파일

```
backend/api/routes.py - Orchestrator 연결
```

---

## 🧩 컴포넌트 상세

### 1. Intent Classifier

**파일**: `backend/agents/intent_classifier.py`

**책임**:
- 사용자 입력을 5가지 의도로 분류
- LLM 기반 Few-shot 분류
- Pydantic Structured Output으로 파싱

**분류 로직**:

| 키워드 | Intent |
|--------|--------|
| "퀴즈", "quiz", "문제", "학습" | `quiz` |
| "메일", "email", "이메일", "검토", "초안" | `email_coach` |
| "실수", "주의", "리스크", "예방" | `risk_detect` |
| 무역 관련 일반 질문 | `general_chat` |
| 무역 무관 | `out_of_scope` |

**코드 스켈레톤**:
```python
from backend.ports import LLMGateway
from typing import Literal

class IntentClassifier:
    """LLM 기반 의도 분류기"""

    INTENTS = Literal["quiz", "email_coach", "risk_detect", "general_chat", "out_of_scope"]

    def __init__(self, llm: LLMGateway):
        self._llm = llm
        self._prompt_template = self._load_prompt()

    def classify(self, user_input: str, context: dict) -> INTENTS:
        """
        사용자 입력을 5가지 의도로 분류

        Returns:
            "quiz" | "email_coach" | "risk_detect" | "general_chat" | "out_of_scope"
        """
        prompt = self._build_classification_prompt(user_input, context)
        response = self._llm.invoke(prompt, temperature=0.0)
        intent = self._parse_intent(response)
        return intent

    def _load_prompt(self) -> str:
        """backend/prompts/intent_classification_prompt.txt 로드"""
        with open("backend/prompts/intent_classification_prompt.txt", "r", encoding="utf-8") as f:
            return f.read()

    def _build_classification_prompt(self, user_input: str, context: dict) -> str:
        """Few-shot 프롬프트 생성"""
        return self._prompt_template.format(
            user_input=user_input,
            context=context
        )

    def _parse_intent(self, response: str) -> INTENTS:
        """LLM 응답에서 의도 추출"""
        # Pydantic Structured Output 파싱 로직
        # 예: "intent: email_coach" → "email_coach"
        pass
```

---

### 2. Orchestrator (LangGraph Workflow)

**파일**: `backend/agents/orchestrator.py`

**책임**:
- LangGraph Workflow 정의
- 의도 분류 → 조건부 라우팅 → 에이전트 실행 → 응답 포맷팅
- 기존 EmailAgent 래핑 (수정 없음)

**Workflow 구조**:
```
START
  ↓
classify_intent (의도 분류)
  ↓
conditional_routing (5-way branching)
  ├─ email_coach → email_agent_node
  ├─ quiz → quiz_agent_node (준비)
  ├─ risk_detect → risk_detect_node (준비)
  ├─ general_chat → general_chat_node
  └─ out_of_scope → general_chat_node
  ↓
format_response (공통 포맷팅)
  ↓
END
```

**코드 스켈레톤**:
```python
from langgraph.graph import StateGraph, END
from backend.agents.intent_classifier import IntentClassifier
from backend.agents.email.email_agent import EmailAgent
from backend.ports import LLMGateway, DocumentRetriever

class Orchestrator:
    """Multi-Agent Orchestrator (LangGraph 기반)"""

    def __init__(self, llm: LLMGateway, retriever: DocumentRetriever):
        self._llm = llm
        self._retriever = retriever
        self._classifier = IntentClassifier(llm)
        self._email_agent = EmailAgent(llm, retriever)  # 기존 EmailAgent 그대로

        # LangGraph Workflow 빌드
        self._workflow = self._build_workflow()

    def _build_workflow(self) -> StateGraph:
        """LangGraph Workflow 구성"""
        workflow = StateGraph(AgentState)

        # 노드 추가
        workflow.add_node("classify_intent", self._classify_intent_node)
        workflow.add_node("email_agent", self._email_agent_node)
        workflow.add_node("quiz_agent", self._quiz_stub_node)
        workflow.add_node("risk_detect", self._risk_detect_stub_node)
        workflow.add_node("general_chat", self._general_chat_node)
        workflow.add_node("format_response", self._format_response_node)

        # 조건부 라우팅 (5-way)
        workflow.add_conditional_edges(
            "classify_intent",
            self._route_by_intent,
            {
                "email_coach": "email_agent",
                "quiz": "quiz_agent",
                "risk_detect": "risk_detect",
                "general_chat": "general_chat",
                "out_of_scope": "general_chat",
            }
        )

        # 각 에이전트 → format_response
        for agent_node in ["email_agent", "quiz_agent", "risk_detect", "general_chat"]:
            workflow.add_edge(agent_node, "format_response")

        # 최종 종료
        workflow.add_edge("format_response", END)

        # 시작점 설정
        workflow.set_entry_point("classify_intent")

        return workflow.compile()

    def _classify_intent_node(self, state: AgentState) -> AgentState:
        """Step 1: 의도 분류"""
        try:
            intent = self._classifier.classify(state["user_input"], state["context"])
            state["intent"] = intent
        except Exception as e:
            state["error"] = f"Intent classification error: {e}"
            state["intent"] = "general_chat"  # 폴백
        return state

    def _route_by_intent(self, state: AgentState) -> str:
        """조건부 라우팅 로직"""
        return state["intent"]

    def _email_agent_node(self, state: AgentState) -> AgentState:
        """Email Agent 노드 (기존 EmailAgent 래핑)"""
        try:
            result = self._email_agent.run(state["user_input"], state["context"])
            state["response"] = result.response
            state["metadata"] = result.metadata
        except Exception as e:
            state["error"] = f"Email agent error: {e}"
            state["response"] = "이메일 검토 중 오류가 발생했습니다. 다시 시도해주세요."
            state["metadata"] = {"error": True}
        return state

    def _quiz_stub_node(self, state: AgentState) -> AgentState:
        """Quiz Agent 준비 (미구현)"""
        state["response"] = "📝 **퀴즈 기능 준비 중**\n\n무역 용어 학습 퀴즈 기능은 곧 제공됩니다."
        state["metadata"] = {"agent_type": "quiz", "status": "not_implemented"}
        return state

    def _risk_detect_stub_node(self, state: AgentState) -> AgentState:
        """Risk Detection Agent 준비 (미구현)"""
        state["response"] = "⚠️ **리스크 감지 기능 준비 중**\n\n업무 상황별 예상 실수 감지 기능은 곧 제공됩니다."
        state["metadata"] = {"agent_type": "risk_detect", "status": "not_implemented"}
        return state

    def _general_chat_node(self, state: AgentState) -> AgentState:
        """일반 질문 응답"""
        # RAG 기반 간단한 Q&A
        state["response"] = "무역 관련 질문에 답변드립니다. 더 구체적인 질문을 해주세요."
        state["metadata"] = {"agent_type": "general_chat"}
        return state

    def _format_response_node(self, state: AgentState) -> AgentState:
        """공통 응답 포맷팅"""
        # 에러가 있으면 에러 메시지 추가
        if state.get("error"):
            state["response"] += f"\n\n_Debug: {state['error']}_"
        return state

    def run(self, user_input: str, context: dict) -> AgentResponse:
        """Orchestrator 실행"""
        initial_state: AgentState = {
            "user_input": user_input,
            "intent": "general_chat",  # 기본값
            "context": context,
            "response": "",
            "metadata": {},
            "error": None
        }

        final_state = self._workflow.invoke(initial_state)

        return AgentResponse(
            response=final_state["response"],
            agent_type=final_state["intent"],
            metadata=final_state["metadata"]
        )
```

---

### 3. 기존 EmailAgent 통합 전략

**핵심**: EmailAgent는 **단 한 줄도 수정하지 않음**

```python
def _email_agent_node(self, state: AgentState) -> AgentState:
    # 기존 EmailAgent.run() 그대로 호출
    result = self._email_agent.run(state["user_input"], state["context"])

    # 결과를 State에 반영
    state["response"] = result.response
    state["metadata"] = result.metadata
    return state
```

**재사용 범위**:
- ✅ Phase 6 완성된 EmailAgent 전체
  - ReviewService (RiskDetector, ToneAnalyzer, TradeTermValidator, UnitValidator)
  - DraftService
  - ResponseFormatter
- ✅ Phase 6 ChromaDB 임베딩 (498 documents)
- ✅ Phase 6 테스트 (`test_email_validation.py`)

**장점**:
- 검증 완료된 코드 그대로 활용
- 테스트 재실행만으로 검증 가능
- 향후 EmailAgent 개선 시 Orchestrator 수정 불필요

---

## 🚨 에러 핸들링 & 폴백

### 에러 처리 전략

| 에러 상황 | 폴백 동작 |
|-----------|-----------|
| 의도 분류 실패 | `general_chat`으로 라우팅 |
| EmailAgent 실패 | "오류 발생" 메시지 + 재시도 안내 |
| LLM API 장애 | "서비스 일시 중단" 메시지 |
| RAG 검색 실패 | "관련 정보를 찾을 수 없습니다" 메시지 |

### 에러 핸들링 코드 패턴

```python
def _email_agent_node(self, state: AgentState) -> AgentState:
    try:
        result = self._email_agent.run(state["user_input"], state["context"])
        state["response"] = result.response
        state["metadata"] = result.metadata
    except Exception as e:
        # 에러 로깅
        logger.error(f"Email agent error: {e}")

        # State에 에러 기록
        state["error"] = str(e)
        state["response"] = "이메일 검토 중 오류가 발생했습니다. 다시 시도해주세요."
        state["metadata"] = {"error": True}

    return state
```

---

## 🧪 테스트 전략

### 1. 의도 분류 테스트

**파일**: `tests/test_intent_classifier.py`

```python
import pytest
from backend.agents.intent_classifier import IntentClassifier

def test_email_intent():
    classifier = IntentClassifier(llm)

    assert classifier.classify("이메일 검토해줘", {}) == "email_coach"
    assert classifier.classify("메일 초안 작성", {}) == "email_coach"
    assert classifier.classify("email review please", {}) == "email_coach"

def test_quiz_intent():
    assert classifier.classify("퀴즈 풀어볼래", {}) == "quiz"
    assert classifier.classify("문제 내줘", {}) == "quiz"

def test_risk_detect_intent():
    assert classifier.classify("실수할 만한 부분 알려줘", {}) == "risk_detect"
    assert classifier.classify("주의할 점은?", {}) == "risk_detect"

def test_general_chat_intent():
    assert classifier.classify("FOB가 뭐야?", {}) == "general_chat"

def test_out_of_scope_intent():
    assert classifier.classify("날씨 어때?", {}) == "out_of_scope"
```

### 2. Orchestrator 통합 테스트

**파일**: `tests/test_orchestrator.py`

```python
import pytest
from backend.agents.orchestrator import Orchestrator

def test_email_workflow():
    orchestrator = Orchestrator(llm, retriever)

    result = orchestrator.run("이메일 검토: We ship via FOB", {})

    assert result.agent_type == "email_coach"
    assert "리스크" in result.response or "톤" in result.response

def test_quiz_stub():
    result = orchestrator.run("퀴즈 내줘", {})

    assert result.agent_type == "quiz"
    assert "준비 중" in result.response

def test_risk_detect_stub():
    result = orchestrator.run("실수할 만한 부분 알려줘", {})

    assert result.agent_type == "risk_detect"
    assert "준비 중" in result.response
```

### 3. 기존 EmailAgent 회귀 테스트

**파일**: `test_email_validation.py` (Phase 6 테스트 재사용)

```bash
# 회귀 테스트 실행
uv run python test_email_validation.py

# 예상 결과:
# ✅ 리스크 탐지: 4건
# ✅ 톤 분석: 7.0/10
# ✅ 무역 용어 검증: 3개 검증
# ✅ 단위 검증: 표준화 제안
```

**검증 항목**:
- [ ] Phase 6 기능 모두 정상 작동
- [ ] 응답 시간 15초 이내 유지
- [ ] RAG 검색 정상 작동 (498 documents)

---

## 📋 구현 체크리스트

### Phase 1: Intent Classifier 구현 (2-3시간)

- [ ] `backend/prompts/intent_classification_prompt.txt` 작성 (Few-shot 프롬프트)
- [ ] `backend/agents/intent_classifier.py` 구현
  - [ ] `classify()` 메서드
  - [ ] `_build_classification_prompt()` 메서드
  - [ ] `_parse_intent()` 메서드
- [ ] 의도 분류 테스트 작성 (`tests/test_intent_classifier.py`)
- [ ] 테스트 통과 확인

### Phase 2: Orchestrator 구현 (3-4시간)

- [ ] `backend/agents/orchestrator.py` 구현
  - [ ] `_build_workflow()` - LangGraph Workflow 정의
  - [ ] `_classify_intent_node()` - 의도 분류 노드
  - [ ] `_email_agent_node()` - EmailAgent 래핑 노드
  - [ ] `_quiz_stub_node()` - Quiz stub 노드
  - [ ] `_risk_detect_stub_node()` - Risk Detection stub 노드
  - [ ] `_general_chat_node()` - 일반 질문 노드
  - [ ] `_format_response_node()` - 응답 포맷팅 노드
  - [ ] `_route_by_intent()` - 조건부 라우팅 로직
- [ ] 에러 핸들링 추가 (try-except 블록)

### Phase 3: API 연동 (1시간)

- [ ] `backend/api/routes.py` 수정
  - [ ] Orchestrator 인스턴스 생성
  - [ ] `/api/chat` 엔드포인트를 Orchestrator로 라우팅
- [ ] FastAPI 서버 재시작 확인

### Phase 4: 테스트 & 검증 (2-3시간)

- [ ] 통합 테스트 작성 (`tests/test_orchestrator.py`)
- [ ] 회귀 테스트 실행 (`test_email_validation.py`)
- [ ] End-to-End 테스트
  - [ ] "이메일 검토해줘" → email_coach 라우팅 확인
  - [ ] "퀴즈 내줘" → quiz stub 확인
  - [ ] "실수 알려줘" → risk_detect stub 확인
- [ ] 응답 시간 측정 (목표: 15초 이내)
- [ ] 에러 핸들링 테스트 (LLM API 장애 시뮬레이션)

---

## 📊 예상 작업 시간

| Phase | 작업 | 예상 시간 |
|-------|------|-----------|
| Phase 1 | Intent Classifier 구현 | 2-3시간 |
| Phase 2 | Orchestrator 구현 | 3-4시간 |
| Phase 3 | API 연동 | 1시간 |
| Phase 4 | 테스트 & 검증 | 2-3시간 |
| **총합** | - | **8-11시간** |

---

## 🎯 완료 기준

### 필수 (Must Have)

- [x] 의도 분류 정확도 90% 이상 (테스트 기준)
- [x] EmailAgent 기능 100% 유지 (회귀 테스트 통과)
- [x] 3가지 의도 정상 라우팅 (email_coach, quiz, risk_detect)
- [x] 응답 시간 15초 이내
- [x] 에러 발생 시 폴백 정상 작동

### 선택 (Nice to Have)

- [ ] 의도 분류 신뢰도(confidence) 표시
- [ ] 대화 히스토리 기반 컨텍스트 유지
- [ ] 통계 대시보드 (의도별 사용 빈도)

---

## 🚀 향후 확장 계획

### Quiz Agent 구현 (향후)

- 퀴즈 생성 로직
- 채점 및 해설
- 난이도 자동 조정

### Risk Detection Agent 구현 (향후)

- 업무 상황별 예상 실수 TOP 3
- 예방 체크리스트 자동 생성

---

## 📚 참고 문서

- [Phase 6 구현 보고서](../PHASE6_IMPLEMENTATION_REPORT.md)
- [Email Agent 워크플로우](../EMAIL_AGENT_WORKFLOW.md)
- [Gap Analysis](../EMAIL_AGENT_GAP_ANALYSIS.md)
- [기획서](../AI Workflow Design 기획서_완성본.md)
- [CLAUDE.md](../../CLAUDE.md)

---

**설계 승인**: 대기 중
**다음 단계**: 구현 계획 작성 (writing-plans 스킬)
