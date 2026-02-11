# 벡터 DB 구축 & 임베딩 완벽 가이드 📚

> **TradeOnboarding Agent의 RAG 시스템 전체 흐름 이해하기**

---

## 📋 목차

1. [전체 흐름 한눈에 보기](#전체-흐름-한눈에-보기)
2. [핵심 구성 요소](#핵심-구성-요소)
3. [상세 동작 과정](#상세-동작-과정)
4. [파일별 역할](#파일별-역할)
5. [데이터 흐름](#데이터-흐름)
6. [사용 방법](#사용-방법)
7. [트러블슈팅](#트러블슈팅)

---

## 🎯 전체 흐름 한눈에 보기

```
┌─────────────────────────────────────────────────────────────────┐
│                    서버 시작 (main.py)                          │
│              uv run uvicorn backend.main:app --reload           │
└─────────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                  Startup Event 트리거                            │
│            (@app.on_event("startup"))                            │
└─────────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│            ChromaDB 컬렉션 확인 (chroma_client.py)              │
│         get_or_create_collection()                               │
│         → backend/vectorstore/ 디렉토리 확인                     │
│         → "trade_coaching_knowledge" 컬렉션 생성/로드            │
└─────────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
                  ┌───────────────┐
                  │ 문서 수 체크  │
                  │ count() > 0?  │
                  └───┬───────┬───┘
                      │       │
                 YES  │       │  NO
                      │       │
                      ▼       ▼
            ┌─────────┐   ┌──────────────────────────────────┐
            │  스킵   │   │   자동 데이터 임베딩 시작       │
            │         │   │   (ingest.py)                    │
            └─────────┘   └──────────┬───────────────────────┘
                                     │
                                     ▼
                   ┌─────────────────────────────────────────┐
                   │  dataset/*.json 파일 로드               │
                   │  • company_domain.json                  │
                   │  • emails.json                          │
                   │  • quiz_samples.json                    │
                   │  • trade_qa.json                        │
                   │  • mistakes.json                        │
                   │  • ... (총 13개 파일)                   │
                   └──────────┬──────────────────────────────┘
                              │
                              ▼
                   ┌─────────────────────────────────────────┐
                   │  각 JSON Entry 처리                     │
                   │  for entry in data:                     │
                   │    1. content 추출                      │
                   │    2. metadata 정규화 (schema.py)       │
                   │    3. embedding 생성 (embedder.py)      │
                   └──────────┬──────────────────────────────┘
                              │
                              ▼
                   ┌─────────────────────────────────────────┐
                   │  Upstage Solar Embedding API 호출       │
                   │  (embedder.py → get_embedding())        │
                   │                                         │
                   │  POST https://api.upstage.ai/v1/        │
                   │       embeddings                        │
                   │  {                                      │
                   │    "input": "문서 내용",                │
                   │    "model": "embedding-query"           │
                   │  }                                      │
                   │                                         │
                   │  응답: [0.123, -0.456, ...] (벡터)     │
                   └──────────┬──────────────────────────────┘
                              │
                              ▼
                   ┌─────────────────────────────────────────┐
                   │  ChromaDB에 문서 추가                   │
                   │  collection.add(                        │
                   │    embeddings=벡터,                     │
                   │    documents=텍스트,                    │
                   │    metadatas=메타데이터,                │
                   │    ids=고유ID                           │
                   │  )                                      │
                   └──────────┬──────────────────────────────┘
                              │
                              ▼
                   ┌─────────────────────────────────────────┐
                   │  배치로 모든 문서 업로드                │
                   │  (10개씩 진행 로그 출력)                │
                   └──────────┬──────────────────────────────┘
                              │
                              ▼
                   ┌─────────────────────────────────────────┐
                   │  ✅ 완료!                               │
                   │  "데이터 임베딩 완료! 총 문서 수: 235" │
                   └─────────────────────────────────────────┘
                              │
                              ▼
            ┌─────────────────────────────────────────────────┐
            │              🎉 서버 시작 완료!                 │
            │    http://localhost:8000                        │
            │    RAG 시스템 준비 완료                         │
            └─────────────────────────────────────────────────┘
```

---

## 🧩 핵심 구성 요소

### 1. **ChromaDB** (벡터 데이터베이스)
- **역할**: 텍스트 임베딩을 벡터로 저장하고 유사도 검색 제공
- **저장 위치**: `backend/vectorstore/`
- **특징**: 로컬에서 작동하는 경량 벡터 DB (별도 서버 불필요)

### 2. **Upstage Solar Embedding API**
- **역할**: 텍스트를 고차원 벡터로 변환
- **모델**: `embedding-query`
- **API 엔드포인트**: `https://api.upstage.ai/v1/embeddings`

### 3. **데이터셋** (`dataset/*.json`)
- **역할**: 무역·물류 도메인 지식을 구조화된 JSON 형태로 저장
- **파일 개수**: 13개
- **총 데이터 포인트**: 200개 이상

### 4. **RAG 시스템 코드**
```
backend/rag/
├── chroma_client.py   # ChromaDB 클라이언트 관리
├── embedder.py        # Upstage API 임베딩 생성
├── ingest.py          # 데이터 로드 & 임베딩 업로드
├── schema.py          # 메타데이터 정규화
└── retriever.py       # 벡터 검색 (나중에 사용)
```

---

## 📖 상세 동작 과정

### Step 1: 서버 시작 및 Startup Event

**파일**: `backend/main.py`

```python
@app.on_event("startup")
async def startup_event():
    # 1. 서버 시작 시 자동 실행
    logger.info("🚀 무역 온보딩 AI 코치 API 시작 중...")
```

- FastAPI의 `@app.on_event("startup")` 데코레이터 사용
- 서버가 시작되면 **한 번만** 자동 실행
- 비동기 함수로 서버 시작 속도에 영향 최소화

---

### Step 2: ChromaDB 컬렉션 확인

**파일**: `backend/rag/chroma_client.py`

```python
# ChromaDB 클라이언트 초기화
_client = chromadb.PersistentClient(path=VECTOR_DB_DIR)

def get_or_create_collection():
    # "trade_coaching_knowledge" 컬렉션 가져오기 또는 생성
    collection = _client.get_or_create_collection(name=COLLECTION_NAME)
    return collection
```

**동작 과정**:
1. `backend/vectorstore/` 디렉토리 확인
2. 없으면 자동 생성
3. `trade_coaching_knowledge` 컬렉션 확인
   - 있으면 → 기존 컬렉션 로드
   - 없으면 → 새 컬렉션 생성

---

### Step 3: 문서 개수 확인

**파일**: `backend/main.py`

```python
collection = get_or_create_collection()
current_count = collection.count()  # 현재 문서 수 확인

if current_count == 0:
    # 비어있으면 자동 임베딩 시작
    ingest_data(reset=False)
else:
    # 이미 있으면 스킵
    logger.info(f"✅ 총 {current_count}개 문서 로드 완료.")
```

**분기 처리**:
- `count() == 0` → 자동 임베딩 시작
- `count() > 0` → 스킵 (이미 데이터 있음)

---

### Step 4: 데이터 로드 (`ingest.py`)

**파일**: `backend/rag/ingest.py`

```python
# dataset 디렉토리의 모든 JSON 파일 로드
json_files = glob.glob(os.path.join(DATASET_DIR, "*.json"))

for file_path in json_files:
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)  # JSON 파싱
```

**JSON 파일 구조 예시**:
```json
[
  {
    "id": 1,
    "category": "trade_terminology",
    "content": "FOB (Free On Board)는 본선인도조건으로...",
    "metadata": {
      "topic": ["incoterms"],
      "level": "beginner",
      "priority": "high"
    }
  }
]
```

---

### Step 5: 메타데이터 정규화 (`schema.py`)

**파일**: `backend/rag/schema.py`

```python
def normalize_metadata(entry: Dict, source_file: str) -> Dict:
    # 1. 기본 스키마 적용
    normalized = UNIFIED_METADATA_SCHEMA.copy()

    # 2. 파일명으로 document_type 추론
    if "emails.json" in source_file:
        normalized["document_type"] = "email"

    # 3. 빈 값 제거, 리스트 정렬
    normalized["topic"] = sorted(list(set(topics)))

    return normalized
```

**목적**:
- 일관된 메타데이터 구조 보장
- 검색 시 필터링 용이
- 빈 값, 중복 제거

---

### Step 6: 임베딩 생성 (`embedder.py`)

**파일**: `backend/rag/embedder.py`

```python
def get_embedding(text: str) -> List[float]:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "input": text,
        "model": "embedding-query"
    }

    response = requests.post(UPSTAGE_API_URL, headers=headers, json=payload)
    data = response.json()

    return data["data"][0]["embedding"]  # 벡터 반환
```

**Upstage API 흐름**:
```
입력 텍스트: "FOB는 본선인도조건으로..."
       ↓
Upstage Solar Embedding API
       ↓
출력 벡터: [0.123, -0.456, 0.789, ...] (1536차원)
```

**에러 처리**:
- 최대 3회 재시도 (exponential backoff)
- 타임아웃: 10초
- 빈 텍스트 체크

---

### Step 7: ChromaDB에 업로드

**파일**: `backend/rag/ingest.py`

```python
# 배치로 모든 문서 추가
collection.add(
    embeddings=embeddings_to_add,      # 벡터 리스트
    documents=documents_to_add,        # 원본 텍스트
    metadatas=metadatas_to_add,        # 메타데이터
    ids=ids_to_add                     # 고유 ID
)
```

**저장 데이터 구조**:
```
ID: "company_domain_1"
Document: "FOB는 본선인도조건으로..."
Embedding: [0.123, -0.456, 0.789, ...]
Metadata: {
  "document_type": "terminology",
  "topic": ["incoterms"],
  "level": "beginner",
  "source_dataset": "company_domain.json"
}
```

---

## 📁 파일별 역할

### `backend/main.py` (FastAPI 진입점)
**역할**: 서버 시작 시 벡터 DB 자동 초기화
```python
@app.on_event("startup")
async def startup_event():
    collection = get_or_create_collection()
    if collection.count() == 0:
        ingest_data(reset=False)
```

---

### `backend/rag/chroma_client.py` (ChromaDB 클라이언트)
**역할**: ChromaDB 연결 및 컬렉션 관리
- `get_or_create_collection()`: 컬렉션 가져오기/생성
- `reset_collection()`: 컬렉션 초기화 (재구축 시 사용)

---

### `backend/rag/embedder.py` (임베딩 생성)
**역할**: Upstage Solar API로 텍스트 → 벡터 변환
- `get_embedding(text)`: 텍스트를 입력받아 임베딩 벡터 반환
- 재시도 로직, 에러 처리 포함

---

### `backend/rag/ingest.py` (데이터 임베딩 & 업로드)
**역할**: 데이터셋 전체를 ChromaDB에 임베딩
- JSON 파일 로드
- 메타데이터 정규화
- 임베딩 생성
- ChromaDB에 배치 업로드

---

### `backend/rag/schema.py` (메타데이터 정규화)
**역할**: 메타데이터 통일된 스키마 적용
- 빈 값 제거
- 타입 강제 (리스트/문자열)
- document_type 자동 추론

---

### `backend/config.py` (환경 설정)
**역할**: `.env` 파일에서 설정 로드
```python
class Settings(BaseSettings):
    upstage_api_key: str
    vector_db_dir: str = "backend/vectorstore"
    collection_name: str = "trade_coaching_knowledge"
    auto_ingest_on_startup: bool = True
```

---

## 🔄 데이터 흐름

### 전체 데이터 파이프라인

```
dataset/company_domain.json
         ↓ (JSON 로드)
[ { "id": 1, "content": "FOB는...", "metadata": {...} } ]
         ↓ (Entry 순회)
"FOB는 본선인도조건으로..."
         ↓ (임베딩 생성)
[0.123, -0.456, 0.789, ...]
         ↓ (메타데이터 정규화)
{
  "document_type": "terminology",
  "topic": ["incoterms"],
  "level": "beginner"
}
         ↓ (ChromaDB 저장)
backend/vectorstore/
  └─ trade_coaching_knowledge/
       ├─ chroma.sqlite3 (메타데이터)
       └─ *.bin (벡터 데이터)
```

---

## 🚀 사용 방법

### 1️⃣ 자동 모드 (권장) - 서버 시작 시 자동 구축

```bash
# 프로젝트 루트에서 실행
cd trade-onboarding-agent

# 서버 시작 → 자동으로 벡터 DB 구축
uv run uvicorn backend.main:app --reload
```

**예상 로그 (첫 실행 시)**:
```
🚀 무역 온보딩 AI 코치 API 시작 중...
📊 벡터 데이터베이스 확인 중...
✅ 벡터 데이터베이스 연결 완료. 현재 문서 수: 0
📥 벡터 데이터베이스가 비어있습니다. 자동 데이터 임베딩 시작...
⏳ 첫 실행 시 수 분이 소요될 수 있습니다...

--- Starting Data Ingestion ---
Processing file: company_domain.json
  Processed 10 entries...
  Processed 20 entries...
Processing file: emails.json
  Processed 30 entries...
...

✅ 데이터 임베딩 완료! 총 문서 수: 235
🎉 서버 시작 완료!
```

**예상 로그 (이후 실행 시)**:
```
🚀 무역 온보딩 AI 코치 API 시작 중...
📊 벡터 데이터베이스 확인 중...
✅ 벡터 데이터베이스 연결 완료. 현재 문서 수: 235
✅ 벡터 데이터베이스에 이미 데이터가 있습니다. 임베딩 생략.
📚 총 235개 문서 로드 완료.
🎉 서버 시작 완료!
```

---

### 2️⃣ 수동 모드 - 직접 데이터 임베딩

```bash
# 데이터 임베딩만 실행 (서버 시작 없이)
uv run python backend/rag/ingest.py

# 기존 데이터 삭제하고 재구축
uv run python backend/rag/ingest.py --reset
```

**사용 시나리오**:
- 서버 시작 전에 미리 임베딩하고 싶을 때
- 데이터셋 변경 후 재구축 필요할 때
- 자동 임베딩 비활성화 상태에서 수동 실행

---

### 3️⃣ 자동 임베딩 비활성화

`.env` 파일 수정:
```bash
AUTO_INGEST_ON_STARTUP=false
```

**효과**:
- 서버 시작 시 임베딩 자동 실행 안 함
- 빈 벡터 DB일 때 경고 메시지만 표시
- 수동 임베딩 필요

---

## 🛠 트러블슈팅

### ❌ 문제 1: "UPSTAGE_API_KEY not found"

**원인**: `.env` 파일에 API 키가 없음

**해결**:
```bash
# .env 파일에 API 키 추가
echo "UPSTAGE_API_KEY=your_actual_api_key_here" >> .env
```

---

### ❌ 문제 2: 임베딩 API 호출 실패

**로그**:
```
HTTP error occurred (Attempt 1/3): 401 Unauthorized
Error: Invalid or expired UPSTAGE_API_KEY.
```

**원인**: API 키가 잘못되었거나 만료됨

**해결**:
1. Upstage Console에서 API 키 재발급
2. `.env` 파일 업데이트
3. 서버 재시작

---

### ❌ 문제 3: 벡터 DB 손상 (권한 오류, 파일 깨짐)

**로그**:
```
sqlite3.OperationalError: database is locked
```

**해결**:
```bash
# 벡터 DB 디렉토리 삭제
rm -rf backend/vectorstore

# 서버 재시작 → 자동 재구축
uv run uvicorn backend.main:app --reload
```

---

### ❌ 문제 4: 임베딩 중 서버가 멈춤

**원인**: 첫 실행 시 200+ 문서 임베딩에 시간 소요 (정상)

**예상 시간**:
- 문서 200개 기준: 약 2~5분
- Upstage API 응답 속도에 따라 변동

**확인 방법**:
```bash
# 로그에서 진행 상황 확인
Processing file: company_domain.json
  Processed 10 entries...  ← 10개씩 진행 로그
  Processed 20 entries...
```

**강제 중단 후 재시작해도 안전** (멱등성 보장)

---

### ❌ 문제 5: 데이터 업데이트 후 반영 안 됨

**원인**: 기존 벡터 DB에 이전 데이터가 남아있음

**해결**:
```bash
# 방법 1: 벡터 DB 재구축 (스크립트)
uv run python backend/rag/ingest.py --reset

# 방법 2: 벡터 DB 삭제 후 서버 재시작
rm -rf backend/vectorstore
uv run uvicorn backend.main:app --reload
```

---

## 🎓 추가 학습 자료

### 관련 개념

**1. 임베딩 (Embedding)**
- 텍스트를 수치 벡터로 변환
- 의미적으로 유사한 텍스트는 유사한 벡터를 가짐
- 차원: 보통 512~1536차원

**2. 벡터 데이터베이스**
- 벡터 간 유사도 검색 (Cosine Similarity)
- 고차원 벡터를 효율적으로 저장/검색
- ChromaDB, Pinecone, Weaviate 등

**3. RAG (Retrieval-Augmented Generation)**
```
사용자 질문 → 벡터 검색 → 관련 문서 찾기 → LLM에 전달 → 답변 생성
```

---

### 참고 문서

- **ChromaDB 공식 문서**: https://docs.trychroma.com/
- **Upstage Solar API**: https://console.upstage.ai/docs
- **FastAPI Events**: https://fastapi.tiangolo.com/advanced/events/

---

## 📊 현재 프로젝트 통계

| 항목 | 수치 |
|------|------|
| **총 데이터셋 파일** | 13개 |
| **총 데이터 포인트** | 200개+ |
| **임베딩 차원** | 1536차원 |
| **벡터 DB 크기** | 약 50~100MB |
| **첫 실행 임베딩 시간** | 2~5분 |
| **이후 서버 시작 시간** | 1~2초 |

---

## 🔗 관련 파일 참조

- **프로젝트 메인 가이드**: `CLAUDE.md`
- **환경 세팅**: `SETUP.md`
- **README**: `README.md`
- **환경 변수 예시**: `.env.example`

---

**마지막 업데이트**: 2026-02-11
