# Email Coach Agent 완전 가이드

> **무역 이메일 작성·검토 AI 코치**
> RAG 기반 리스크 탐지, 톤 분석, 자동 개선 제안

---

## 📋 목차

1. [개요](#개요)
2. [주요 기능](#주요-기능)
3. [아키텍처](#아키텍처)
4. [API 사용법](#api-사용법)
5. [RAG 시스템](#rag-시스템)
6. [워크플로우](#워크플로우)
7. [설치 및 실행](#설치-및-실행)
8. [예시](#예시)
9. [트러블슈팅](#트러블슈팅)
10. [개발 히스토리](#개발-히스토리)

---

## 개요

### 무엇인가?

**Email Coach Agent**는 무역·물류 업계 신입사원을 위한 이메일 작성 코칭 AI입니다.

**핵심 가치:**
- 🎯 **실수 예방**: 301개 실제 사례 기반으로 리스크 자동 탐지
- 🌍 **문화권별 톤 최적화**: 일본/미국/중동 등 수신자 국가에 맞는 톤 제안
- ⚡ **즉각 피드백**: 30초 내 5W1H 체크리스트 + 개선안 제공
- 📚 **RAG 기반**: 실제 우수 이메일 템플릿과 실수 사례 참조

### 왜 필요한가?

**문제점:**
- 신입사원의 90%가 이메일로 인한 클레임 경험 (결제 조건 누락, 톤 문제 등)
- 선배 검토 대기 시간: 평균 2-3일
- 문화권별 커뮤니케이션 스타일 학습 부재

**해결책:**
- AI가 24시간 즉시 검토
- 301개 실제 사례 데이터 기반 피드백
- Draft(작성) + Review(검토) 2가지 모드 제공

---

## 주요 기능

### 1. Draft Mode (이메일 초안 작성)

**입력:**
```json
{
  "user_input": "일본 거래처에 FOB 조건으로 100톤 주문하는 이메일 작성",
  "context": {
    "recipient_country": "Japan",
    "product": "steel pipes",
    "quantity": "100 tons"
  }
}
```

**출력:**
- ✅ 완성된 이메일 초안 (Subject + Body + Signature)
- ✅ 5W1H 체크리스트 (누락 항목 표시)
- ✅ 참고한 우수 이메일 템플릿 (RAG 출처)

**특징:**
- 수신자 국가별 인사말 자동 조정 (Dear/님/san 등)
- Incoterms, 결제 조건, 납기 자동 구조화
- 비즈니스 이메일 필수 요소 자동 포함

---

### 2. Review Mode (이메일 검토 및 개선)

**입력:**
```json
{
  "email_content": "Hi, I need 100 units. Send quickly.",
  "context": {
    "recipient_country": "Japan",
    "business_relationship": "new_client"
  }
}
```

**출력:**
- 🚨 **리스크 탐지** (5개까지, CRITICAL/MEDIUM/LOW)
- 🎨 **톤 분석** (현재 톤 점수/10, 권장 톤)
- 📝 **완전한 개선 이메일**
- 💡 **개선 포인트** (Before/After 비교)
- 📚 **참고 자료** (RAG 출처)

**리스크 카테고리:**
- `missing_product_specification`: 제품 사양 누락
- `missing_payment_terms`: 결제 조건 누락
- `missing_incoterms`: 무역 조건 누락
- `aggressive_tone`: 공격적/명령조 톤
- `missing_shipment_date`: 납기일 미명시
- `missing_attachment`: 첨부 파일 누락

**톤 카테고리:**
- `professional`: 표준 비즈니스 (미국/유럽)
- `polite`: 정중한 표현 (일본/한국)
- `formal`: 격식 있는 표현 (중동/관공서)
- `friendly`: 친근한 표현 (기존 거래처)

---

## 아키텍처

### 전체 구조

```
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI Endpoint                         │
│                 POST /api/email/draft                       │
│                 POST /api/email/review                      │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   EmailCoachAgent                           │
│                   (Facade Pattern)                          │
│  - _detect_mode() → "draft" or "review"                   │
│  - Delegates to DraftService or ReviewService              │
└─────────────────────────────────────────────────────────────┘
                              │
                 ┌────────────┴────────────┐
                 ▼                         ▼
        ┌────────────────┐       ┌────────────────┐
        │ DraftService   │       │ ReviewService  │
        │ (222 lines)    │       │ (301 lines)    │
        └────────────────┘       └────────────────┘
                 │                         │
                 │                         ├─→ RiskDetector
                 │                         ├─→ ToneAnalyzer
                 │                         └─→ ChecklistGenerator
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│                 ChromaDocumentRetriever                     │
│  - 301 documents (12 types)                                │
│  - Upstage Solar Embedding (4096 dim)                      │
│  - search(query, k, document_type, **filters)             │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   Upstage Solar LLM                         │
│  - Model: solar-pro                                        │
│  - Timeout: 30s                                            │
│  - Retry: 3회 (exponential backoff)                       │
└─────────────────────────────────────────────────────────────┘
```

### 핵심 컴포넌트

#### 1. EmailCoachAgent (163 lines)
- **역할**: 의도 탐지 + 라우팅
- **패턴**: Facade Pattern
- **책임**:
  - Draft/Review 모드 자동 감지
  - 적절한 서비스로 위임
  - 응답 포맷팅

**파일**: `backend/agents/email/email_agent.py`

```python
class EmailCoachAgent(BaseAgent):
    def run(self, user_input: str, context: Dict) -> AgentResponse:
        mode = self._detect_mode(user_input, context)

        if mode == "draft":
            return self._draft_service.generate_draft(user_input, context)
        else:
            return self._review_service.review_email(user_input, context)
```

---

#### 2. DraftService (222 lines)
- **역할**: 이메일 초안 작성
- **워크플로우**:
  1. RAG 검색 (우수 이메일 템플릿 3-5개)
  2. LLM 호출 (프롬프트 + 템플릿 참고)
  3. 5W1H 체크리스트 생성
  4. 응답 포맷팅

**파일**: `backend/agents/email/draft_service.py`

**주요 메서드**:
- `generate_draft()`: 전체 워크플로우
- `_search_email_templates()`: RAG 검색
- `_generate_email()`: LLM 호출
- `_validate_5w1h()`: 체크리스트 생성

---

#### 3. ReviewService (301 lines)
- **역할**: 이메일 검토 + 개선
- **워크플로우**:
  1. RAG 검색 (실수 사례 + 우수 이메일)
  2. RiskDetector 호출 → 리스크 탐지
  3. ToneAnalyzer 호출 → 톤 분석
  4. LLM 호출 → 개선 이메일 생성
  5. 응답 포맷팅

**파일**: `backend/agents/email/review_service.py`

**주요 메서드**:
- `review_email()`: 전체 워크플로우
- `_search_references()`: RAG 검색 (mistakes + emails)
- `_generate_improvement()`: LLM으로 개선안 생성

---

#### 4. RiskDetector (203 lines)
- **역할**: 이메일 리스크 자동 탐지
- **방식**: LLM 기반 + 3-tier Fallback
- **출력**: 최대 5개 리스크 (CRITICAL → MEDIUM → LOW 순)

**파일**: `backend/agents/email/risk_detector.py`

**Fallback 로직**:
```python
def detect(self, email_content, retrieved_mistakes, context):
    response = llm.invoke(prompt)

    # Tier 1: JSON block 파싱
    if "```json" in response:
        risks = parse_json_block(response)
    # Tier 2: 전체 JSON 파싱
    elif response.startswith("{"):
        risks = json.loads(response)
    # Tier 3: 텍스트 파싱
    else:
        risks = parse_text_format(response)

    return sorted(risks, key=severity)[:5]
```

---

#### 5. ToneAnalyzer (126 lines)
- **역할**: 문화권별 톤 분석
- **평가 기준**: 0-10점 (10점 = 완벽한 톤)
- **고려 요소**:
  - 수신자 국가 (Japan → polite, USA → professional)
  - 비즈니스 관계 (new_client → formal, existing → friendly)
  - 명령조/공격적 표현 감지

**파일**: `backend/agents/email/tone_analyzer.py`

---

#### 6. ChromaDocumentRetriever (200+ lines)
- **역할**: 벡터 데이터베이스 검색
- **데이터**: 301개 문서 (12종 타입)
- **임베딩**: Upstage Solar Embedding (4096 차원)

**파일**: `backend/infrastructure/chroma_retriever.py`

**주요 기능**:
```python
def search(query: str, k: int = 5, document_type: str = None):
    # 1. 쿼리를 Upstage API로 임베딩
    query_embeddings = self._embedding_function([query])

    # 2. ChromaDB 검색
    results = self._collection.query(
        query_embeddings=query_embeddings,
        n_results=k,
        where={"document_type": document_type}
    )

    return [RetrievedDocument(...) for doc in results]
```

---

#### 7. ResponseFormatter (214 lines)
- **역할**: 모든 응답을 마크다운 형식으로 변환
- **패턴**: Static Methods Only

**파일**: `backend/agents/email/response_formatter.py`

**주요 메서드**:
- `format_draft_response()`: Draft 응답 포맷팅
- `format_review_response()`: Review 응답 포맷팅
- `format_risks()`: 리스크 마크다운 변환
- `format_tone_analysis()`: 톤 분석 마크다운 변환

---

## API 사용법

### Endpoint 1: Draft Mode

**URL**: `POST /api/email/draft`

**Request**:
```json
{
  "user_input": "미국 거래처에 CIF 조건으로 200톤 견적 요청하는 이메일 작성",
  "context": {
    "recipient_country": "USA",
    "product": "copper wire",
    "quantity": "200 tons",
    "business_relationship": "existing_client"
  }
}
```

**Response**:
```json
{
  "response": "### 📧 작성된 이메일 초안\n\n```\nSubject: Price Quotation Request...",
  "agent_type": "email",
  "metadata": {
    "mode": "draft",
    "checklist": {
      "what": true,
      "when": true,
      "where": true,
      "who": true,
      "how": true,
      "how_much": true
    },
    "retrieved_emails": 3,
    "sources": ["emails.json", "emails.json", "emails.json"]
  }
}
```

**cURL 예시**:
```bash
curl -X POST http://localhost:8000/api/email/draft \
  -H "Content-Type: application/json" \
  -d '{
    "user_input": "일본 거래처에 FOB 조건 견적 요청",
    "context": {
      "recipient_country": "Japan",
      "product": "steel pipes"
    }
  }'
```

---

### Endpoint 2: Review Mode

**URL**: `POST /api/email/review`

**Request**:
```json
{
  "email_content": "Hi,\n\nI need 100 units of your product ASAP.\n\nSend me the quote.\n\nThanks",
  "context": {
    "recipient_country": "Japan",
    "business_relationship": "new_client"
  }
}
```

**Response**:
```json
{
  "response": "### 🚨 발견된 리스크 (5건)\n\n**1. [🔴 CRITICAL] missing_product_specification**...",
  "agent_type": "email",
  "metadata": {
    "mode": "review",
    "risks": [
      {
        "type": "missing_product_specification",
        "severity": "critical",
        "location": "line 2",
        "current": "I need 100 units of your product",
        "risk": "제품 사양 누락으로 잘못된 품목 발송 가능성",
        "recommendation": "Product: [Product Name/Model], Quantity: 100 units (10kg/box)",
        "source": "mistakes.json#mistake_01"
      }
    ],
    "risk_count": 5,
    "tone_score": 3.5,
    "current_tone": "aggressive",
    "retrieved_mistakes": 5,
    "retrieved_emails": 2,
    "sources": ["mistakes.json", "mistakes.json", "emails.json"]
  }
}
```

**cURL 예시**:
```bash
curl -X POST http://localhost:8000/api/email/review \
  -H "Content-Type: application/json" \
  -d '{
    "email_content": "Hi, send me 100 units quickly.",
    "context": {
      "recipient_country": "Japan"
    }
  }'
```

---

## RAG 시스템

### 데이터 구조

**총 301개 문서, 12가지 타입**:

| Document Type | 개수 | 설명 | 사용 모드 |
|--------------|------|------|-----------|
| `email` | 50+ | 우수 이메일 템플릿 | Draft, Review |
| `common_mistake` | 20+ | 실수 사례 | Review |
| `claim_type` | 15+ | 클레임 유형 | Review |
| `error_checklist` | 10+ | 오류 체크리스트 | Review |
| `terminology` | 50+ | 무역 용어 | Draft |
| `country_guideline` | 30+ | 국가별 가이드라인 | Draft, Review |
| `process_flow` | 20+ | 프로세스 플로우 | Draft |
| 기타 | 106 | FAQ, KPI, CEO 가이드 등 | - |

**출처 파일**: `dataset/*.json` (13개 JSON 파일)

---

### 임베딩 방식

**모델**: Upstage Solar Embedding (`embedding-query`)
**차원**: 4096
**API**: `https://api.upstage.ai/v1/embeddings`

**데이터 임베딩 과정**:
```bash
# 1. 데이터 임베딩 및 저장
uv run python backend/rag/ingest.py --reset

# 2. 301개 문서가 backend/vectorstore에 저장
# - Collection: trade_coaching_knowledge
# - Embedding: Upstage Solar (4096 dim)
```

**검색 과정**:
```python
# 1. 쿼리를 Upstage API로 임베딩
query_embedding = upstage_api.embed("FOB 조건")  # → [0.123, -0.456, ...]

# 2. ChromaDB에서 유사도 검색
results = chroma.query(
    query_embeddings=[query_embedding],
    n_results=5,
    where={"document_type": "email"}
)

# 3. 거리 기반 정렬 (낮을수록 유사)
# Distance: 0.61 (매우 유사) ~ 1.5 (보통)
```

---

### RAG 검색 전략

#### Draft Mode
```python
# 우수 이메일 템플릿 검색
retrieved_emails = retriever.search(
    query=user_input,
    k=3,
    document_type="email"
)
```

#### Review Mode
```python
# 1. 실수 사례 검색
retrieved_mistakes = retriever.search(
    query=email_content,
    k=5,
    document_type="common_mistake"
)

# 2. 우수 이메일 검색
retrieved_emails = retriever.search(
    query=email_content,
    k=3,
    document_type="email"
)
```

---

### RAG 품질 보장

**3가지 메커니즘**:

1. **거리 임계값 필터링**:
   - Distance < 1.0: 매우 관련성 높음
   - Distance < 1.5: 관련성 있음
   - Distance >= 1.5: 제외

2. **메타데이터 필터링**:
   ```python
   retriever.search(
       query="FOB 조건",
       document_type="email",
       country="Japan"  # 추가 필터
   )
   ```

3. **출처 추적**:
   - 모든 리스크에 `source` 필드 포함
   - 예: `"source": "mistakes.json#mistake_01"`

---

## 워크플로우

### Draft Mode 워크플로우

```
사용자 요청
    ↓
┌──────────────────────────────────────┐
│ 1. Mode Detection                   │
│    "작성", "draft" 키워드 감지      │
└──────────────────────────────────────┘
    ↓
┌──────────────────────────────────────┐
│ 2. RAG Search (Email Templates)     │
│    - Query: user_input               │
│    - Type: email                     │
│    - K: 3개                          │
│    - Result: 우수 이메일 템플릿     │
└──────────────────────────────────────┘
    ↓
┌──────────────────────────────────────┐
│ 3. LLM Call (Draft Generation)      │
│    Prompt:                           │
│    - 사용자 요청: {user_input}      │
│    - 수신자 국가: {country}         │
│    - 참고 템플릿: {retrieved_emails}│
│                                      │
│    Output: 완성된 이메일 초안       │
└──────────────────────────────────────┘
    ↓
┌──────────────────────────────────────┐
│ 4. 5W1H Checklist                    │
│    - What: 제품명 포함 여부          │
│    - When: 납기일 포함 여부          │
│    - Where: Incoterms 포함 여부      │
│    - Who: 수신자/발신자 명시         │
│    - How: 배송 방법 명시             │
│    - How Much: 결제 조건 명시        │
└──────────────────────────────────────┘
    ↓
┌──────────────────────────────────────┐
│ 5. Response Formatting               │
│    Markdown 형식으로 변환:           │
│    - 📧 이메일 초안                  │
│    - ✅ 체크리스트                   │
│    - 📚 참고 자료 (RAG 출처)        │
└──────────────────────────────────────┘
    ↓
API 응답 반환
```

---

### Review Mode 워크플로우

```
사용자 이메일 입력
    ↓
┌──────────────────────────────────────┐
│ 1. Mode Detection                   │
│    "검토", "review" 키워드 또는     │
│    email_content 필드 존재 시       │
└──────────────────────────────────────┘
    ↓
┌──────────────────────────────────────┐
│ 2. RAG Search (Parallel)             │
│                                      │
│  A. Mistake Search                   │
│     - Query: email_content           │
│     - Type: common_mistake           │
│     - K: 5개                         │
│                                      │
│  B. Email Search                     │
│     - Query: email_content           │
│     - Type: email                    │
│     - K: 3개                         │
└──────────────────────────────────────┘
    ↓
┌──────────────────────────────────────┐
│ 3. Risk Detection (RiskDetector)     │
│                                      │
│    LLM Prompt:                       │
│    - 원본 이메일: {email_content}   │
│    - 참고 실수: {retrieved_mistakes} │
│    - 수신자 국가: {country}         │
│                                      │
│    Output:                           │
│    - 최대 5개 리스크                │
│    - Severity: CRITICAL/MEDIUM/LOW   │
│    - Source: mistakes.json#id        │
│                                      │
│    Fallback:                         │
│    JSON block → Full JSON → Text     │
└──────────────────────────────────────┘
    ↓
┌──────────────────────────────────────┐
│ 4. Tone Analysis (ToneAnalyzer)      │
│                                      │
│    LLM Prompt:                       │
│    - 원본 이메일: {email_content}   │
│    - 수신자 국가: {country}         │
│    - 비즈니스 관계: {relationship}  │
│                                      │
│    Output:                           │
│    - 현재 톤: aggressive/polite/...  │
│    - 톤 점수: 0-10                   │
│    - 권장 톤: professional/formal    │
│    - 문제점: ["명령조", "과도한..."]│
└──────────────────────────────────────┘
    ↓
┌──────────────────────────────────────┐
│ 5. Improvement Generation            │
│                                      │
│    LLM Prompt:                       │
│    - 원본 이메일: {email_content}   │
│    - 리스크: {risks}                 │
│    - 현재 톤: {current_tone}        │
│    - 권장 톤: {recommended_tone}    │
│    - 참고 이메일: {retrieved_emails}│
│                                      │
│    Output:                           │
│    - 완전히 다시 작성된 개선 이메일 │
│    - 모든 리스크 해결                │
│    - 권장 톤 적용                    │
└──────────────────────────────────────┘
    ↓
┌──────────────────────────────────────┐
│ 6. Response Formatting               │
│                                      │
│    Markdown 구조:                    │
│    - 🚨 리스크 (5건)                │
│    - 🎨 톤 분석                      │
│    - 📝 수정안 (Before/After)       │
│    - 💡 개선 포인트                  │
│    - 📚 참고 자료 (RAG 출처)        │
└──────────────────────────────────────┘
    ↓
API 응답 반환
```

---

## 설치 및 실행

### 1. 환경 세팅

```bash
# 프로젝트 루트로 이동
cd trade-onboarding-agent

# 의존성 설치 (uv 사용)
uv sync

# 환경 변수 설정
cp .env.example .env
# .env 파일에 UPSTAGE_API_KEY 입력
```

### 2. 데이터 임베딩 (최초 1회)

```bash
# RAG 데이터 임베딩
uv run python backend/rag/ingest.py --reset

# 출력 예시:
# Processing file: emails.json
# Processing file: mistakes.json
# ...
# Total entries processed: 301
# Current collection count: 301
```

### 3. 서버 실행

```bash
# FastAPI 서버 시작
uv run uvicorn backend.main:app --reload

# 출력 예시:
# INFO: Uvicorn running on http://127.0.0.1:8000
# ✅ 벡터 데이터베이스 연결 완료. 현재 문서 수: 301
# 🎉 서버 시작 완료!
```

### 4. 상태 확인

```bash
# Health check
curl http://localhost:8000/health
# → {"status":"healthy"}

# API 문서
open http://localhost:8000/docs
```

---

## 예시

### 예시 1: Draft Mode - 견적 요청 이메일

**입력**:
```json
{
  "user_input": "일본 거래처에 FOB 부산항 조건으로 Steel Pipe 200톤 견적 요청하는 이메일 작성해줘. 납기는 3월 15일이고 결제는 T/T 30/70으로 하고 싶어.",
  "context": {
    "recipient_country": "Japan",
    "product": "Steel Pipe",
    "quantity": "200 tons",
    "business_relationship": "existing_client"
  }
}
```

**출력** (일부):
```markdown
### 📧 작성된 이메일 초안

Subject: Price Quotation Request for Steel Pipe - 200 Tons FOB Busan

Dear Tanaka-san,

I hope this email finds you well.

We are writing to request a price quotation for the following:

- Product: Steel Pipe [Model/Grade]
- Quantity: 200 metric tons
- Incoterms: FOB Busan Port
- Payment Terms: 30% T/T in advance, 70% before shipment
- Requested Delivery: March 15, 2026

Could you please provide us with your best quotation including:
1. Unit price per ton
2. Total amount
3. Production lead time
4. Available payment methods

We would appreciate your prompt reply by [Date].

Thank you for your continued cooperation.

Best regards,
[Your Name]
[Your Company]

---

### ✅ 5W1H 체크리스트

- ✅ What: Steel Pipe 명시
- ✅ When: March 15, 2026
- ✅ Where: FOB Busan Port
- ✅ Who: Tanaka-san
- ✅ How: T/T 30/70
- ✅ How Much: 200 tons

---

### 📚 참고한 우수 이메일 (3개)

1. [높은 유사도] (거리: 0.58)
   출처: emails.json
   내용: FOB → CIF 조건 변경 협의...
```

---

### 예시 2: Review Mode - 문제 많은 이메일 검토

**입력**:
```json
{
  "email_content": "Hey,\n\nSend me 500 units next week. Make sure they're good quality.\n\nThanks",
  "context": {
    "recipient_country": "Germany",
    "business_relationship": "new_client"
  }
}
```

**출력** (일부):
```markdown
### 🚨 발견된 리스크 (5건)

**1. [🔴 CRITICAL] missing_product_specification**
- 현재: "500 units"
- 리스크: 제품명/모델/사양 누락으로 잘못된 제품 발송 가능성
- 권장: Product: [Product Name/Model], Quantity: 500 units (specification details)
- 출처: mistakes.json#mistake_01

**2. [🔴 CRITICAL] missing_payment_terms**
- 현재: 전체 이메일
- 리스크: 결제 조건 미명시로 대금 회수 지연 가능성
- 권장: Payment Terms: T/T 30% deposit, 70% before shipment
- 출처: mistakes.json#mistake_03

**3. [🔴 CRITICAL] missing_incoterms**
- 현재: "Send me 500 units"
- 리스크: 운송 조건 누락으로 비용 분쟁 발생 가능
- 권장: Incoterms: FOB/CIF [Port Name]
- 출처: mistakes.json#mistake_04

**4. [🟡 MEDIUM] aggressive_tone**
- 현재: "Send me", "Make sure"
- 리스크: 명령조 톤으로 인한 비즈니스 관계 악화
- 권장: Could you please provide / We would appreciate
- 출처: mistakes.json#mistake_05

**5. [🟡 MEDIUM] missing_delivery_date**
- 현재: "next week"
- 리스크: 모호한 납기로 생산 계획 수립 불가
- 권장: Required Delivery: [Specific Date, e.g., March 20, 2026]
- 출처: mistakes.json#mistake_04

---

### 🎨 톤 분석 결과

현재 이메일은 매우 비공식적이고 명령조로 작성되어 독일 거래처 (특히 신규)에게 부적절합니다.

**현재 톤**: casual_aggressive
**권장 톤**: professional
**톤 점수**: 2.5/10

**문제점**:
- "Hey" → 비즈니스 이메일에 부적절한 인사
- "Send me" → 명령조 (파트너십 관계 아님)
- "Make sure" → 압박감 전달
- "Thanks" → 너무 간결하고 무성의

---

### 📝 수정안

**Before**:
```
Hey,

Send me 500 units next week. Make sure they're good quality.

Thanks
```

**After**:
```
Subject: Order Request for [Product Name] - 500 Units

Dear [Contact Name],

I hope this email finds you well.

I am [Your Name] from [Your Company], and we are interested in placing an order for your products.

Below are the details of our requirements:

- Product: [Product Name/Model]
- Quantity: 500 units
- Incoterms: [FOB/CIF] [Port Name]
- Payment Terms: T/T 30% deposit upon order confirmation, 70% before shipment
- Requested Delivery: [Specific Date, e.g., March 20, 2026]
- Quality Standards: [ISO certification / specific requirements]

Could you please provide us with:
1. Proforma Invoice
2. Product specifications and certifications
3. Estimated production lead time

We would appreciate your confirmation at your earliest convenience.

Thank you for your cooperation.

Best regards,
[Your Full Name]
[Your Position]
[Your Company Name]
[Contact Information]
```

---

### 💡 개선 포인트

1. ✅ **Product Specification**: [Product Name/Model] 명시
2. ✅ **Payment Terms**: T/T 30/70 추가
3. ✅ **Incoterms**: FOB/CIF [Port] 명시
4. 🎨 **Tone**: "Hey" → "Dear [Name]", "Send me" → "Could you please provide"
5. 🎨 **Delivery**: "next week" → "March 20, 2026" (구체적 날짜)

---

### 📚 참고한 실수 사례 (5개)

1. ⚪ [높은 유사도] (거리: 0.85)
   - 내용: quantity 단위 lb/kg 혼동
   - 출처: mistakes.json

2. ⚪ [높은 유사도] (거리: 0.91)
   - 내용: 포장단위 계산 오류
   - 출처: mistakes.json

...
```

---

## 트러블슈팅

### 문제 1: RAG 검색 결과 0개

**증상**:
```json
{
  "metadata": {
    "retrieved_emails": 0,
    "retrieved_mistakes": 0
  }
}
```

**원인**:
1. ChromaDB 컬렉션 이름 불일치
2. 임베딩 차원 불일치
3. 데이터 미임베딩

**해결**:
```bash
# 1. 데이터 재임베딩
uv run python backend/rag/ingest.py --reset

# 2. 서버 재시작
# (Ctrl+C로 종료 후)
uv run uvicorn backend.main:app --reload

# 3. 확인
curl http://localhost:8000/health
```

---

### 문제 2: 임베딩 차원 오류

**증상**:
```
chromadb.errors.InvalidArgumentError: Collection expecting embedding with dimension of 4096, got 384
```

**원인**:
- ChromaDB가 기본 임베딩(384차원) 사용 중
- Upstage 임베딩(4096차원)과 불일치

**해결**:
`backend/infrastructure/chroma_retriever.py` 확인:
```python
# UpstageEmbeddingFunction이 query 임베딩에 사용되는지 확인
query_embeddings = self._embedding_function([query])
results = self._collection.query(query_embeddings=query_embeddings, ...)
```

---

### 문제 3: ChromaDB 싱글톤 충돌

**증상**:
```
ValueError: An instance of Chroma already exists for backend/vectorstore with different settings
```

**원인**:
- 여러 곳에서 다른 설정으로 ChromaDB 초기화

**해결**:
1. `backend/rag/chroma_client.py` 확인:
   ```python
   _client = chromadb.PersistentClient(path=VECTOR_DB_DIR)
   ```

2. `backend/infrastructure/chroma_retriever.py` 확인:
   ```python
   self._client = chromadb.PersistentClient(
       path="backend/vectorstore"  # settings 파라미터 제거
   )
   ```

---

### 문제 4: LLM 타임아웃

**증상**:
```
RetrievalError: Document search failed: timeout
```

**원인**:
- Upstage API 응답 지연
- 네트워크 문제

**해결**:
1. `backend/infrastructure/upstage_llm.py` 타임아웃 증가:
   ```python
   timeout=60  # 30 → 60초
   ```

2. Retry 로직 확인:
   ```python
   max_retries=3
   retry_delay=2  # exponential backoff
   ```

---

### 문제 5: JSON 파싱 실패

**증상**:
```
ERROR: Risk detection failed: Expecting property name enclosed in double quotes
```

**원인**:
- LLM이 잘못된 JSON 반환

**해결**:
`backend/agents/email/risk_detector.py`의 3-tier Fallback이 작동 중:
```python
# Tier 1: JSON block
if "```json" in response:
    risks = parse_json_block(response)
# Tier 2: Full JSON
elif response.startswith("{"):
    risks = json.loads(response)
# Tier 3: Text parsing
else:
    risks = parse_text_format(response)
```

**로그 확인**:
```bash
tail -f logs/trade_onboarding_debug.log | grep "Fallback"
```

---

### 문제 6: 톤 점수 비정상

**증상**:
- 개선된 이메일이 원본보다 낮은 점수

**원인**:
- RAG 검색 실패로 컨텍스트 부족
- 프롬프트 템플릿 변수 불일치

**해결**:
1. RAG 검색 확인:
   ```bash
   # 검색 테스트
   uv run python -c "
   from backend.config import get_settings
   from backend.infrastructure.chroma_retriever import ChromaDocumentRetriever

   retriever = ChromaDocumentRetriever(get_settings())
   results = retriever.search('FOB 조건', k=3, document_type='email')
   print(f'검색 결과: {len(results)}개')
   "
   ```

2. 프롬프트 템플릿 변수 확인:
   `backend/prompts/email/email_improvement_prompt.txt`:
   ```
   - 현재 톤: {current_tone} (점수: {tone_score}/10)
   - 권장 톤: {recommended_tone}
   - 톤 문제점: {tone_issues}
   ```

---

### 문제 7: 서버 포트 충돌

**증상**:
```
ERROR: [Errno 48] error while attempting to bind on address ('127.0.0.1', 8000): address already in use
```

**해결**:
```bash
# 1. 기존 프로세스 확인
lsof -i :8000

# 2. 프로세스 종료
kill -9 <PID>

# 3. 다른 포트로 실행
uv run uvicorn backend.main:app --port 8001
```

---

## 개발 히스토리

### Phase 1: 초기 구현 (God Class)
- **파일**: `backend/agents/email_coach_agent.py` (997 lines)
- **문제점**:
  - 모든 로직이 하나의 파일에 집중
  - 테스트 어려움
  - 유지보수 곤란

### Phase 2: Hexagonal Architecture 적용
- **목표**: 포트/어댑터 패턴으로 의존성 분리
- **결과**:
  - `DocumentRetriever` 인터페이스 정의
  - `ChromaDocumentRetriever` 구현체 분리
  - `LLMGateway` 인터페이스 정의

### Phase 3: God Class 분해 (현재)
- **목표**: Single Responsibility Principle 적용
- **결과**: 997 lines → 7개 서비스로 분할
  - `EmailCoachAgent` (163 lines) - Facade
  - `DraftService` (222 lines) - Draft 전담
  - `ReviewService` (301 lines) - Review 전담
  - `RiskDetector` (203 lines) - 리스크 탐지
  - `ToneAnalyzer` (126 lines) - 톤 분석
  - `ChecklistGenerator` (68 lines) - 체크리스트
  - `ResponseFormatter` (214 lines) - 응답 포맷팅

### Phase 4: RAG 시스템 최적화
- **문제**: ChromaDB 검색 0건 반환
- **원인**:
  1. 컬렉션 이름 불일치 (`trade_documents` vs `trade_coaching_knowledge`)
  2. 임베딩 차원 불일치 (384 vs 4096)
  3. ChromaDB 싱글톤 충돌
- **해결**:
  1. 컬렉션 이름 통일
  2. `UpstageEmbeddingFunction` 클래스 생성
  3. 쿼리 수동 임베딩
  4. ChromaDB 설정 통일

**결과**: ✅ 301개 문서 정상 검색

---

## 참고 자료

### 주요 파일 위치

```
backend/
├── agents/email/
│   ├── email_agent.py          # Facade (163 lines)
│   ├── draft_service.py        # Draft 로직 (222 lines)
│   ├── review_service.py       # Review 로직 (301 lines)
│   ├── risk_detector.py        # 리스크 탐지 (203 lines)
│   ├── tone_analyzer.py        # 톤 분석 (126 lines)
│   ├── checklist_generator.py  # 체크리스트 (68 lines)
│   └── response_formatter.py   # 포맷팅 (214 lines)
├── infrastructure/
│   ├── chroma_retriever.py     # RAG 검색 (200+ lines)
│   └── upstage_llm.py          # LLM Gateway
├── prompts/email/
│   ├── email_draft_prompt.txt
│   ├── email_improvement_prompt.txt
│   ├── email_risk_detection_prompt.txt
│   └── email_tone_analysis_prompt.txt
└── rag/
    ├── ingest.py               # 데이터 임베딩
    ├── embedder.py             # Upstage Embedding API
    └── chroma_client.py        # ChromaDB 클라이언트

dataset/
├── emails.json                 # 우수 이메일 템플릿
├── mistakes.json               # 실수 사례
└── *.json                      # 기타 11개 파일

docs/
├── EMAIL_AGENT_GUIDE.md        # 이 문서
├── PROJECT_STATUS.md           # 전체 프로젝트 현황
└── REFACTORING_*.md            # 리팩토링 보고서
```

---

### 관련 문서

- **전체 프로젝트**: `docs/PROJECT_STATUS.md`
- **API 문서**: `http://localhost:8000/docs`
- **기획서**: `docs/AI Workflow Design 기획서_완성본.md`
- **CLAUDE.md**: 프로젝트 가이드라인

---

### 코딩 컨벤션

**파일명**: `snake_case.py`
**클래스명**: `PascalCase`
**함수/변수**: `snake_case`
**상수**: `UPPER_SNAKE_CASE`

**커밋 메시지**:
```
feat: 새 기능 추가
fix: 버그 수정
refactor: 리팩토링
docs: 문서 수정
test: 테스트 추가
```

---

## FAQ

### Q1: Draft와 Review 모드는 어떻게 자동으로 구분되나요?

A: `EmailCoachAgent._detect_mode()` 메서드가 다음 기준으로 판단합니다:

```python
def _detect_mode(self, user_input: str, context: Dict) -> str:
    # Review 모드 우선 (email_content 존재)
    if "email_content" in context:
        return "review"

    # Draft 키워드 감지
    draft_keywords = ["작성", "draft", "write", "초안"]
    if any(keyword in user_input.lower() for keyword in draft_keywords):
        return "draft"

    # Review 키워드 감지
    review_keywords = ["검토", "review", "check", "분석"]
    if any(keyword in user_input.lower() for keyword in review_keywords):
        return "review"

    # 기본값: Draft
    return "draft"
```

---

### Q2: RAG 검색이 너무 느린데 어떻게 최적화하나요?

A: 다음 방법들을 고려하세요:

1. **K 값 줄이기**:
   ```python
   retriever.search(query, k=3)  # 5 → 3
   ```

2. **캐싱 추가**:
   ```python
   @lru_cache(maxsize=100)
   def search_cached(query: str, k: int):
       return retriever.search(query, k)
   ```

3. **타임아웃 설정**:
   ```python
   timeout=5  # 5초 이내 응답
   ```

---

### Q3: 새로운 실수 사례를 추가하려면?

A: 다음 단계를 따르세요:

1. **데이터 추가**:
   ```bash
   # dataset/mistakes.json 편집
   {
     "id": "mistake_21",
     "content": "새로운 실수 사례...",
     "document_type": "common_mistake",
     "severity": "critical"
   }
   ```

2. **재임베딩**:
   ```bash
   uv run python backend/rag/ingest.py --reset
   ```

3. **서버 재시작**:
   ```bash
   # Ctrl+C 후
   uv run uvicorn backend.main:app --reload
   ```

---

### Q4: 톤 점수 기준은 무엇인가요?

A: 10점 만점 기준:

- **9-10점**: 완벽한 비즈니스 톤, 문화권 적합
- **7-8점**: 양호, 일부 개선 필요
- **5-6점**: 보통, 여러 개선 필요
- **3-4점**: 부적절, 명령조 또는 비격식
- **0-2점**: 매우 부적절, 비즈니스 이메일 부적합

---

### Q5: 새로운 국가 가이드라인을 추가하려면?

A: 프롬프트 파일 수정:

```bash
# backend/prompts/email/email_tone_analysis_prompt.txt

## 국가별 톤 가이드라인

- **일본/한국**: 정중하고 완곡한 표현 (～していただけますでしょうか)
- **미국/유럽**: 직설적이되 프로페셔널
- **중동**: 격식 있는 표현, 존칭 다용
- **베트남**: 중립적, 명확한 표현  # ← 추가
```

---

## 마무리

Email Coach Agent는 **무역 이메일 작성의 모든 과정을 AI로 지원**합니다.

**핵심 강점**:
- ✅ **실전 데이터 기반**: 301개 실제 사례
- ✅ **문화권별 최적화**: 일본/미국/중동 등 자동 톤 조정
- ✅ **리스크 자동 탐지**: CRITICAL 리스크 사전 방지
- ✅ **즉각 피드백**: 30초 내 완전한 개선안 제공

**향후 개선 방향**:
- [ ] 실시간 스트리밍 응답 (SSE)
- [ ] 이메일 히스토리 추적 (대화 컨텍스트)
- [ ] 다국어 지원 (영어 ↔ 한국어 자동 번역)
- [ ] 첨부 파일 분석 (PDF, Excel)
- [ ] 학습 데이터 자동 업데이트 (사용자 피드백 기반)

---

**문의**: 프로젝트 이슈 또는 팀 Slack 채널
**최종 업데이트**: 2026-02-12
**버전**: v1.0 (Phase 3 완료)
