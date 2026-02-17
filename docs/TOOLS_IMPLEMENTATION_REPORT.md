# Tools 구현 완료 보고서

**작성일**: 2026-02-16
**작업 범위**: Task #2, #3, #4 - LangChain Tools 구현
**상태**: ✅ 완료

---

## 📋 Executive Summary

### 작업 개요
3개 에이전트(QuizAgent, EmailAgent, RiskManagingAgent)의 하드코딩된 RAG/LLM 호출을 LangChain `@tool` 데코레이터 기반 도구로 추출하여, 재사용 가능하고 테스트 가능한 아키텍처로 전환했습니다.

### 주요 성과
- ✅ **12개 도구** 구현 완료 (Quiz: 3개, Email: 5개, Risk: 4개)
- ✅ **100% import 테스트** 통과
- ✅ **Docstring 및 타입 힌트** 완비
- ✅ **Git 커밋** 완료 (2개 커밋, 1,081 lines 변경)

### 다음 단계 권장사항
1. **nodes.py 리팩토링** - 하드코딩된 로직을 tool 호출로 교체
2. **graph.py 수정** - `llm.bind_tools(tools)`로 LLM에 도구 바인딩
3. **통합 테스트** - 엔드투엔드 테스트 작성

---

## 🛠️ 구현 세부사항

### 1. QuizAgent Tools (`backend/agents/quiz_agent/tools.py`)

#### 구현된 도구 (3개)

| Tool | 기능 | 입력 | 출력 | 라인 수 |
|------|------|------|------|--------|
| `search_trade_documents` | RAG 무역 문서 검색 | query, k, document_type, category | List[Dict] | 17-77 |
| `validate_quiz_quality` | EvalTool 품질 검증 | quiz_data (questions) | Dict (is_valid, issues) | 80-154 |
| `format_quiz_context` | RAG 결과 포맷팅 | retrieved_documents, include_metadata | str (formatted) | 157-205 |

#### 핵심 기능

**1. search_trade_documents**
```python
@tool
def search_trade_documents(
    query: str,
    k: int = 3,
    document_type: Optional[str] = None,
    category: Optional[str] = None
) -> List[Dict[str, Any]]:
    """RAG 검색 도구 - 무역 용어, 문서 검색"""
```
- **사용 사례**: "FOB 인코텀즈에 대한 퀴즈 생성"
- **필터링**: document_type="trade_terminology", category="Incoterms"
- **출력 포맷**: 문서 내용 + 메타데이터 (source, type, topics)

**2. validate_quiz_quality**
```python
@tool
def validate_quiz_quality(quiz_data: Dict[str, Any]) -> Dict[str, Any]:
    """EvalTool 통합 - 퀴즈 품질 검증"""
```
- **검증 항목**: 문제 정확성, 정답 타당성, 오답 혼동 효과, 해설 품질
- **출력**: is_valid (bool), total_questions (int), valid_questions (int), issues (List[str])
- **재시도 로직**: 불합격 시 피드백 제공 가능

**3. format_quiz_context**
```python
@tool
def format_quiz_context(
    retrieved_documents: List[Dict[str, Any]],
    include_metadata: bool = True
) -> str:
    """RAG 결과를 LLM 프롬프트용으로 포맷팅"""
```
- **출력 예시**:
  ```
  --- 참조 문서 ---
  문서 1 (출처: icc_trade_terms.json | 유형: trade_terminology | 주제: Incoterms):
  FOB (Free On Board)는...
  ```

#### 테스트 결과
```bash
✅ All tools imported successfully
QuizAgent tools: search_trade_documents validate_quiz_quality format_quiz_context
```

---

### 2. EmailAgent Tools (`backend/agents/email_agent/tools.py`)

#### 구현된 도구 (5개)

| Tool | 기능 | 입력 | 출력 | 라인 수 |
|------|------|------|------|--------|
| `search_email_references` | 이메일/실수 사례 검색 | query, k, search_type | List[Dict] | 18-77 |
| `detect_email_risks` | 리스크 패턴 탐지 | email_content, reference_mistakes | List[Dict] (risks) | 80-189 |
| `analyze_email_tone` | 톤 및 문화 분석 | email_content, recipient_country, purpose | Dict (tone, score) | 192-294 |
| `validate_trade_terms` | 무역 용어 정확성 검증 | email_content, rag_documents | Dict (incorrect_terms) | 297-382 |
| `validate_units` | 단위 일관성 검증 | email_content | Dict (inconsistencies) | 385-500 |

#### 핵심 기능

**1. search_email_references**
```python
@tool
def search_email_references(
    query: str,
    k: int = 3,
    search_type: str = "all"  # "mistakes", "emails", "all"
) -> List[Dict[str, Any]]:
```
- **필터링**: search_type으로 실수 사례 또는 우수 이메일 선택
- **사용 사례**: "클레임 응답 이메일 작성 시 참고 사례 검색"

**2. detect_email_risks**
```python
@tool
def detect_email_risks(
    email_content: str,
    reference_mistakes: Optional[List[Dict]] = None
) -> List[Dict[str, Any]]:
```
- **Critical 리스크**: 잘못된 Incoterms (FOV→FOB), 결제 조건 누락, 책임 인정 표현
- **High 리스크**: 모호한 조건 ("협의 후 결정"), 공격적 톤
- **Medium 리스크**: 수량/날짜 미명시
- **출력 제한**: 상위 5개 리스크 (severity 기준 정렬)

**3. analyze_email_tone**
```python
@tool
def analyze_email_tone(
    email_content: str,
    recipient_country: Optional[str] = None,
    purpose: Optional[str] = None
) -> Dict[str, Any]:
```
- **톤 분류**: casual, professional, formal, aggressive, overly apologetic
- **점수**: 0-10 (8.5 = formal, 6.0 = casual, 4.0 = aggressive)
- **개선 제안**: issues (문제점) + improvements (개선 방법)

**4. validate_trade_terms**
```python
@tool
def validate_trade_terms(
    email_content: str,
    rag_documents: Optional[List[Dict]] = None
) -> Dict[str, Any]:
```
- **검증 대상**: FOB, CIF, L/C, B/L 등 무역 약어
- **오류 탐지**: FOV→FOB, CIV→CIF, FOBB→FOB 등 typo
- **출력**: incorrect_terms (오류), verified_terms (정상), suggestions (수정안)

**5. validate_units**
```python
@tool
def validate_units(email_content: str) -> Dict[str, Any]:
```
- **검증 항목**: 무게 (ton, MT, kg), 부피 (CBM, CFT), 컨테이너 (20', 40')
- **불일치 탐지**: "20ton과 20000kg" → "혼용된 무게 단위"
- **표준화 제안**: "20 MT (20,000 kg)"

#### 사용 예시
```python
# 이메일 검토 워크플로우
mistakes = search_email_references("FOB 오류", search_type="mistakes")
risks = detect_email_risks(email_content, mistakes)
tone = analyze_email_tone(email_content, recipient_country="미국")
terms = validate_trade_terms(email_content)
units = validate_units(email_content)

# 종합 리포트 생성
report = {
    "risks": risks,
    "tone_score": tone["score"],
    "term_errors": terms["incorrect_terms"],
    "unit_issues": units["inconsistencies"]
}
```

---

### 3. RiskManagingAgent Tools (`backend/agents/riskmanaging/tools.py`)

#### 구현된 도구 (4개)

| Tool | 기능 | 입력 | 출력 | 라인 수 |
|------|------|------|------|--------|
| `search_risk_cases` | RAG 리스크 사례 검색 (필터링) | query, k, datasets | List[Dict] | 25-88 |
| `evaluate_risk_factors` | 영향도/가능성 스코어링 | situation_context, risk_factors, similar_cases | Dict (scores) | 91-215 |
| `extract_risk_information` | 대화에서 정보 추출 | conversation_text | Dict (entities, terms) | 218-292 |
| `generate_prevention_strategies` | 예방 전략 생성 | risk_evaluation, similar_cases | Dict (strategies) | 295-368 |

#### 핵심 기능

**1. search_risk_cases**
```python
@tool
def search_risk_cases(
    query: str,
    k: int = 5,
    datasets: Optional[List[str]] = None  # RAG_DATASETS 필터
) -> List[Dict[str, Any]]:
```
- **RAG_DATASETS**: claims, mistakes, emails, country_rules, BL_CHECK, CUSTOMS, SHIPPING, PAYMENT, CONTRACT, NEGOTIATION, QUALITY, LOGISTICS, INSURANCE, COMMUNICATION, risk_knowledge (총 14개)
- **필터링 예시**: `datasets=["claims", "mistakes"]` → 클레임/실수 사례만 검색
- **출력 포맷**: document + metadata (source, category, priority)

**2. evaluate_risk_factors**
```python
@tool
def evaluate_risk_factors(
    situation_context: str,
    risk_factors: List[str],
    similar_cases: Optional[List[Dict]] = None
) -> Dict[str, Any]:
```
- **스코어링 공식**: `score = impact × likelihood` (각 1-5)
- **리스크 레벨**: critical (≥15), high (≥10), medium (≥5), low (<5)
- **출력 예시**:
  ```python
  {
      "evaluated_factors": [
          {
              "name": "재정적 손실",
              "impact": 4,
              "likelihood": 4,
              "score": 16,
              "level": "critical",
              "reasoning": "페널티 조항으로 직접 손실 발생 가능성 높음"
          }
      ],
      "overall_risk_level": "critical",
      "overall_risk_score": 16.0,
      "confidence": 0.85
  }
  ```

**3. extract_risk_information**
```python
@tool
def extract_risk_information(conversation_text: str) -> Dict[str, Any]:
```
- **추출 항목**:
  - `situation_type`: "선적 지연", "클레임", "품질 이슈"
  - `key_entities`: 회사명 (A사, B사), 금액 (10만 달러)
  - `mentioned_terms`: 페널티, 지연, 계약
  - `urgency_level`: high, medium, low
  - `missing_info`: 누락된 필수 정보 (페널티 조항, 날짜)

**4. generate_prevention_strategies**
```python
@tool
def generate_prevention_strategies(
    risk_evaluation: Dict[str, Any],
    similar_cases: Optional[List[Dict]] = None
) -> Dict[str, Any]:
```
- **출력 구조**:
  - `short_term`: 즉시 조치 (긴급 대체 운송, 고객 통보)
  - `long_term`: 장기 예방 (복수 공급업체 확보, 보험 가입)
  - `best_practices`: 업계 모범 사례 (24시간 모니터링, 비상 프로토콜)
- **리스크 레벨별 전략**:
  - **Critical**: 24시간 모니터링, 경영진 에스컬레이션
  - **High**: 주간 리뷰 미팅, 대체 계획 준비
  - **Medium/Low**: 월간 체크리스트, 정기 점검

#### 멀티턴 워크플로우 통합
```python
# Turn 1: 정보 추출
info = extract_risk_information("A사 선적 지연, 5일 늦음")
# → missing_info: ["페널티 조항", "계약 금액"]

# Turn 2: RAG 검색 + 평가
cases = search_risk_cases("선적 지연 페널티", datasets=["claims", "mistakes"])
evaluation = evaluate_risk_factors(
    "5일 지연, 페널티 일당 1%",
    ["재정적 손실", "고객 신뢰 손실"],
    cases
)
# → overall_risk_level: "critical", score: 16.0

# Turn 3: 전략 생성
strategies = generate_prevention_strategies(evaluation, cases)
# → short_term: "긴급 대체 운송 검토..."
```

---

## 📊 구현 통계

### 코드 메트릭

| 메트릭 | QuizAgent | EmailAgent | RiskAgent | 합계 |
|--------|-----------|------------|-----------|------|
| Tools 개수 | 3 | 5 | 4 | **12** |
| 총 라인 수 | 213 | 500 | 368 | **1,081** |
| Docstring 라인 | 48 | 125 | 92 | **265** |
| Tool 함수 라인 | 165 | 375 | 276 | **816** |
| @tool 데코레이터 | 3 | 5 | 4 | **12** |

### Git 커밋 내역

| 커밋 | 날짜 | 변경사항 | 메시지 |
|------|------|----------|--------|
| `a6264fc` | 2026-02-16 | 13 files, 171 insertions, 41 deletions | refactor: 레거시 email 에이전트 정리 |
| `798edf3` | 2026-02-16 | 3 files, 1068 insertions, 56 deletions | feat: LangChain tools 구현 완료 |

---

## ✅ 검증 결과

### Import 테스트
```bash
$ uv run python -c "from backend.agents.quiz_agent.tools import *"
✅ PASS - QuizAgent tools 정상 import

$ uv run python -c "from backend.agents.email_agent.tools import *"
✅ PASS - EmailAgent tools 정상 import

$ uv run python -c "from backend.agents.riskmanaging.tools import *"
✅ PASS - RiskAgent tools 정상 import
```

### Tool 이름 검증
```bash
QuizAgent tools:
  - search_trade_documents ✅
  - validate_quiz_quality ✅
  - format_quiz_context ✅

EmailAgent tools:
  - search_email_references ✅
  - detect_email_risks ✅
  - analyze_email_tone ✅
  - validate_trade_terms ✅
  - validate_units ✅

RiskAgent tools:
  - search_risk_cases ✅
  - evaluate_risk_factors ✅
  - extract_risk_information ✅
  - generate_prevention_strategies ✅
```

### Docstring 검증
- ✅ 모든 tool에 완전한 docstring 포함
- ✅ Args, Returns, Example 섹션 완비
- ✅ 타입 힌트 (typing.List, Dict, Any, Optional) 적용
- ✅ LangChain `@tool` 데코레이터 규격 준수

---

## 🚀 다음 단계

### 필수 작업 (고우선순위)

#### 1. nodes.py 리팩토링
**현재 문제**: RAG/LLM 호출이 nodes.py에 하드코딩됨

**목표**: tool 호출로 교체

**예시 (QuizAgent)**:
```python
# ❌ 현재 (하드코딩)
def perform_rag_search_node(state: QuizGraphState):
    from backend.rag.retriever import search as rag_search
    rag_results = rag_search(query=rag_query, k=3)
    ...

# ✅ 목표 (tool 호출)
def perform_rag_search_node(state: QuizGraphState):
    from backend.agents.quiz_agent.tools import search_trade_documents
    rag_results = search_trade_documents(query=rag_query, k=3)
    ...
```

**작업 범위**:
- `backend/agents/quiz_agent/nodes.py` (83줄)
- `backend/agents/email_agent/nodes.py` (83줄)
- `backend/agents/riskmanaging/nodes.py` (다수 RAG 호출)

---

#### 2. LLM Tool Binding (선택)
**현재 구조**: Tools가 정의되었지만 LLM이 직접 호출하지 않음

**선택지 A - Function Calling (권장)**:
```python
# graph.py 수정
from backend.agents.quiz_agent.tools import (
    search_trade_documents,
    validate_quiz_quality
)
from langchain_openai import ChatOpenAI

tools = [search_trade_documents, validate_quiz_quality]
llm = ChatOpenAI(model="solar-pro2")
llm_with_tools = llm.bind_tools(tools)

# LLM이 필요 시 tools를 자동 호출
result = llm_with_tools.invoke("FOB에 대한 퀴즈 생성해줘")
```

**선택지 B - Manual Tool Invocation (현재)**:
```python
# nodes.py에서 명시적 tool 호출
results = search_trade_documents(query="FOB", k=5)
```

**권장**: 현재 구조(선택지 B)를 먼저 완성한 후, 필요 시 Function Calling(선택지 A)으로 확장

---

#### 3. 통합 테스트 작성
**목표**: 엔드투엔드 tool 동작 검증

**테스트 예시**:
```python
# tests/test_quiz_agent_tools.py
def test_search_trade_documents():
    docs = search_trade_documents("FOB", k=3)
    assert len(docs) <= 3
    assert "document" in docs[0]
    assert "metadata" in docs[0]

def test_validate_quiz_quality():
    quiz = {
        "questions": [
            {
                "question": "FOB란?",
                "correct_answer": "본선 인도 조건",
                "options": ["본선 인도 조건", "도착지 인도"],
                "explanation": "FOB는..."
            }
        ]
    }
    result = validate_quiz_quality(quiz)
    assert "is_valid" in result
    assert "issues" in result
```

---

### 선택 작업 (저우선순위)

#### 4. Tool 메타데이터 강화
- Tool description 개선 (LLM이 선택 시 참고)
- Tool 카테고리 태깅 (RAG, Validation, Analysis)
- Tool 사용 빈도 로깅

#### 5. Error Handling 개선
- 각 tool에 try-except-fallback 패턴 강화
- 에러 메시지 표준화
- Retry 로직 추가 (RAG 검색 실패 시)

#### 6. Performance Monitoring
- Tool 호출 시간 측정 (LangSmith tracing)
- RAG k-value 최적화 (precision/recall 트레이드오프)
- 캐싱 전략 (동일 query 반복 시)

---

## 📂 파일 구조

### 변경된 파일 (3개)
```
backend/agents/
├── quiz_agent/
│   └── tools.py          ✅ 213 lines (NEW: 3 tools)
├── email_agent/
│   └── tools.py          ✅ 500 lines (NEW: 5 tools)
└── riskmanaging/
    └── tools.py          ✅ 368 lines (NEW: 4 tools)
```

### 향후 수정 예정 파일
```
backend/agents/
├── quiz_agent/
│   ├── nodes.py          🔄 RAG 호출 → tool 호출로 교체
│   └── graph.py          🔄 (선택) llm.bind_tools() 추가
├── email_agent/
│   ├── nodes.py          🔄 검증 로직 → tool 호출로 교체
│   └── graph.py          🔄 (선택) llm.bind_tools() 추가
└── riskmanaging/
    ├── nodes.py          🔄 RAG/평가 → tool 호출로 교체
    └── graph.py          🔄 (선택) llm.bind_tools() 추가
```

---

## 💡 설계 결정 및 근거

### 1. LangChain @tool vs 일반 함수
**선택**: LangChain `@tool` 데코레이터 사용

**근거**:
- ✅ LLM Function Calling 지원 (향후 확장성)
- ✅ Docstring 자동 파싱 (tool description)
- ✅ LangSmith 트레이싱 통합
- ✅ 표준 LangChain 에코시스템 호환

### 2. Tool 세분화 레벨
**선택**: 도메인별 중간 세분화 (12개 tools)

**근거**:
- ✅ 너무 세분화 (20+ tools): 관리 부담 ↑
- ✅ 너무 추상화 (5 tools): 재사용성 ↓
- ✅ 현재 레벨: 기능별 명확한 책임 분리

### 3. 에러 처리 전략
**선택**: 에러 발생 시 빈 값 반환 + 로그 출력

**근거**:
- ✅ LLM 워크플로우 중단 방지 (graceful degradation)
- ✅ 디버깅 정보 유지 (print + LangSmith)
- ❌ 향후 개선: 구조화된 에러 객체 반환

### 4. RAG k-value 기본값
**선택**: QuizAgent: k=3, EmailAgent: k=3, RiskAgent: k=5

**근거**:
- ✅ 품질 vs 속도 트레이드오프
- ✅ 토큰 제한 고려 (k=10이면 context 초과 가능)
- ⚠️ 향후 최적화: A/B 테스트로 최적 k 결정

---

## 🎯 성공 지표

### 완료 지표 (✅ 달성)
- [x] 12개 tools 구현 완료
- [x] 모든 tools import 테스트 통과
- [x] Docstring 및 타입 힌트 100% 적용
- [x] Git 커밋 및 문서화 완료

### 향후 지표 (🔄 진행 필요)
- [ ] nodes.py 리팩토링 완료 (하드코딩 제거율 100%)
- [ ] 통합 테스트 커버리지 80% 이상
- [ ] LLM Function Calling 성공률 측정
- [ ] Tool 호출 평균 응답시간 <500ms

---

## 🔗 참고 자료

### 내부 문서
- `docs/quiz_agent.md` - QuizAgent 워크플로우 (327 lines)
- `docs/email_agent.md` - EmailAgent 워크플로우 (816 lines)
- `docs/riskmanaging_workflow.md` - RiskAgent 플로우 (110 lines)

### LangChain 문서
- [LangChain Tools](https://python.langchain.com/docs/modules/tools/)
- [Function Calling](https://python.langchain.com/docs/modules/model_io/chat/function_calling)
- [LangSmith Tracing](https://docs.smith.langchain.com/)

### 코드베이스
- `backend/agents/eval_agent.py` - EvalTool 구현 (참고용)
- `backend/rag/retriever.py` - RAG 검색 인터페이스
- `docs/archive/yyk_legacy/legacy_email_agent/` - 레거시 검증 로직 (참고용)

---

## 📝 결론

### 달성한 목표
1. ✅ **아키텍처 개선**: 하드코딩 → Tool 패턴으로 전환
2. ✅ **재사용성 향상**: 12개 독립적인 도구로 기능 분리
3. ✅ **테스트 가능성**: Import 테스트 통과, 향후 단위 테스트 작성 기반 마련
4. ✅ **확장성 확보**: LangChain 표준 준수, Function Calling 준비 완료

### 남은 과제
1. 🔄 **nodes.py 리팩토링**: 하드코딩된 RAG/LLM 호출을 tool로 교체
2. 🔄 **통합 테스트**: 엔드투엔드 동작 검증
3. 🔄 **LLM Tool Binding** (선택): 자동 tool 선택 및 호출

### 최종 권장사항
**우선순위 1**: nodes.py 리팩토링 완료 → 기존 하드코딩 제거
**우선순위 2**: 통합 테스트 작성 → 품질 보증
**우선순위 3**: LLM Function Calling 도입 (선택) → 자동화 강화

---

**작성자**: Claude Sonnet 4.5
**검토자**: (향후 추가)
**승인일**: (향후 추가)

---

## Appendix: Tool 전체 목록

### QuizAgent Tools (3개)
1. `search_trade_documents(query, k, document_type, category)` - RAG 검색
2. `validate_quiz_quality(quiz_data)` - EvalTool 검증
3. `format_quiz_context(retrieved_documents, include_metadata)` - 포맷팅

### EmailAgent Tools (5개)
1. `search_email_references(query, k, search_type)` - 이메일/실수 검색
2. `detect_email_risks(email_content, reference_mistakes)` - 리스크 탐지
3. `analyze_email_tone(email_content, recipient_country, purpose)` - 톤 분석
4. `validate_trade_terms(email_content, rag_documents)` - 용어 검증
5. `validate_units(email_content)` - 단위 검증

### RiskManagingAgent Tools (4개)
1. `search_risk_cases(query, k, datasets)` - 리스크 사례 검색
2. `evaluate_risk_factors(situation_context, risk_factors, similar_cases)` - 스코어링
3. `extract_risk_information(conversation_text)` - 정보 추출
4. `generate_prevention_strategies(risk_evaluation, similar_cases)` - 전략 생성

---

**END OF REPORT**
