# Session Store Guide

**작성일**: 2026-02-16
**버전**: 1.0
**작성자**: Task #7 - Redis 통합

---

## 📋 목차

1. [개요](#개요)
2. [아키텍처](#아키텍처)
3. [설정 가이드](#설정-가이드)
4. [개발 환경 설정](#개발-환경-설정)
5. [프로덕션 환경 설정](#프로덕션-환경-설정)
6. [Redis 로컬 테스트](#redis-로컬-테스트)
7. [마이그레이션 가이드](#마이그레이션-가이드)
8. [문제 해결](#문제-해결)

---

## 개요

### 변경 사항 요약

기존 **InMemoryConversationStore**는 서버 재시작 시 모든 세션이 손실되는 문제가 있었습니다.
Task #7에서 **RedisConversationStore**를 추가하여 프로덕션 환경에서 세션 영속성을 확보했습니다.

#### Before (Phase 7 이전)

- **세션 관리**: Python dict (인메모리)
- **영속성**: ❌ 서버 재시작 시 모든 세션 손실
- **확장성**: ❌ 단일 서버만 지원 (다중 인스턴스 불가)
- **TTL**: ❌ 없음 (메모리 누수 가능)

#### After (Phase 7 이후)

- **세션 관리**: Redis (선택 가능) 또는 InMemory (개발용)
- **영속성**: ✅ Redis 재시작에도 세션 유지 (RDB/AOF 설정 시)
- **확장성**: ✅ 다중 FastAPI 인스턴스에서 세션 공유 가능
- **TTL**: ✅ 1시간 자동 만료 (설정 가능)

---

## 아키텍처

### 클래스 다이어그램

```mermaid
classDiagram
    class ConversationStore {
        <<abstract>>
        +get_state(session_id)
        +save_state(session_id, state)
        +delete_state(session_id)
        +create_new_session_id()
    }

    class InMemoryConversationStore {
        -_store: Dict
        +get_state(session_id)
        +save_state(session_id, state)
        +delete_state(session_id)
        +create_new_session_id()
    }

    class RedisConversationStore {
        -redis_client: Redis
        -ttl: int
        +get_state(session_id)
        +save_state(session_id, state)
        +delete_state(session_id)
        +create_new_session_id()
        +extend_ttl(session_id)
        +get_all_session_ids()
    }

    ConversationStore <|-- InMemoryConversationStore
    ConversationStore <|-- RedisConversationStore
```

### 파일 구조

```
backend/agents/orchestrator/
├── session_store.py          # 세션 스토어 구현 (NEW)
│   ├── ConversationStore      # 추상 베이스 클래스
│   ├── InMemoryConversationStore
│   ├── RedisConversationStore
│   └── create_conversation_store()  # Factory 함수
├── nodes.py                  # 오케스트레이터 노드 (UPDATED)
│   └── OrchestratorComponents  # 스토어 사용
├── graph.py
└── state.py
```

### 세션 데이터 구조

Redis에 저장되는 세션 데이터 형식:

```python
{
    "active_agent": str | None,  # "quiz", "email", "riskmanaging", "default_chat"
    "conversation_history": [
        {"role": "User", "content": "사용자 메시지"},
        {"role": "Agent", "content": "AI 응답"}
    ],
    "agent_specific_state": {
        "analysis_in_progress": bool  # RiskManagingAgent 전용
    },
    "last_interaction_timestamp": float  # Unix timestamp
}
```

**Redis 키 형식**: `session:<UUID>`
**예시**: `session:123e4567-e89b-12d3-a456-426614174000`

---

## 설정 가이드

### 환경 변수 (.env)

#### 개발 환경 (기본값)

```bash
# Redis Session Store
USE_REDIS_SESSION=false  # InMemory 사용
SESSION_TTL=3600
```

#### 프로덕션 환경 (Redis 사용)

**옵션 1: REDIS_URL 사용 (권장 - 클라우드 서비스)**

```bash
USE_REDIS_SESSION=true
REDIS_URL=redis://username:password@host:port/db
SESSION_TTL=3600

# 예시 (Redis Cloud)
REDIS_URL=redis://:mypassword@redis-12345.c1.us-east-1.amazonaws.com:6379/0

# 예시 (AWS ElastiCache with SSL)
REDIS_URL=rediss://:mypassword@my-cluster.abc123.0001.use1.cache.amazonaws.com:6379/0
```

**옵션 2: 개별 파라미터 사용 (로컬/자체 호스팅)**

```bash
USE_REDIS_SESSION=true
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=your_redis_password
REDIS_DB=0
REDIS_SSL=false
SESSION_TTL=3600
```

### config.py 설정 항목

| 설정 항목 | 기본값 | 설명 |
|----------|-------|------|
| `use_redis_session` | `False` | `True`: Redis 사용, `False`: InMemory 사용 |
| `redis_url` | `""` | Redis 연결 URL (우선순위 높음) |
| `redis_host` | `"localhost"` | Redis 호스트 (redis_url 없을 때) |
| `redis_port` | `6379` | Redis 포트 |
| `redis_password` | `""` | Redis 비밀번호 |
| `redis_db` | `0` | Redis 데이터베이스 번호 (0-15) |
| `redis_ssl` | `False` | SSL/TLS 연결 여부 |
| `session_ttl` | `3600` | 세션 만료 시간 (초) |

---

## 개발 환경 설정

### 로컬 개발 (InMemory 사용)

**특징**:
- Redis 설치 불필요
- 빠른 시작
- 서버 재시작 시 세션 손실 (개발 중 문제 없음)

**설정**:
```bash
# .env 파일
USE_REDIS_SESSION=false
```

**실행**:
```bash
uv run uvicorn backend.main:app --reload
```

**로그 확인**:
```
💾 Using InMemoryConversationStore (development mode)
Orchestrator initialized agent: riskmanaging
Orchestrator initialized agent: quiz
Orchestrator initialized agent: email
Orchestrator initialized agent: default_chat
```

---

## 프로덕션 환경 설정

### Redis 서버 요구사항

- **버전**: Redis 5.0 이상 권장
- **메모리**: 세션 100개당 ~10MB (대략적 추정)
- **영속성**: RDB 또는 AOF 활성화 권장
- **보안**: 비밀번호 설정 필수

### 클라우드 서비스 옵션

#### 1. Redis Cloud (권장 - 무료 30MB 제공)

```bash
# .env 설정
USE_REDIS_SESSION=true
REDIS_URL=redis://:your_password@redis-xxxxx.c1.us-east-1.cloud.redislabs.com:12345/0
SESSION_TTL=3600
```

**장점**:
- 완전 관리형
- 무료 티어 제공
- 자동 백업
- SSL 지원

**가입**: https://redis.com/try-free/

#### 2. AWS ElastiCache

```bash
# .env 설정
USE_REDIS_SESSION=true
REDIS_URL=rediss://:password@my-cluster.abc123.0001.use1.cache.amazonaws.com:6379/0
REDIS_SSL=true
SESSION_TTL=3600
```

**장점**:
- AWS 인프라와 통합
- VPC 내 보안
- 자동 장애 조치

#### 3. Docker Compose (자체 호스팅)

**docker-compose.yml**:
```yaml
version: '3.8'

services:
  redis:
    image: redis:7-alpine
    container_name: trade-agent-redis
    ports:
      - "6379:6379"
    command: >
      redis-server
      --requirepass your_redis_password
      --appendonly yes
      --appendfsync everysec
    volumes:
      - redis_data:/data
    restart: unless-stopped

  fastapi:
    build: .
    ports:
      - "8000:8000"
    environment:
      - USE_REDIS_SESSION=true
      - REDIS_HOST=redis
      - REDIS_PORT=6379
      - REDIS_PASSWORD=your_redis_password
      - SESSION_TTL=3600
    depends_on:
      - redis

volumes:
  redis_data:
```

**실행**:
```bash
docker-compose up -d
```

---

## Redis 로컬 테스트

### 1. Redis 설치

**macOS (Homebrew)**:
```bash
brew install redis
brew services start redis
```

**Ubuntu/Debian**:
```bash
sudo apt update
sudo apt install redis-server
sudo systemctl start redis-server
```

**Docker**:
```bash
docker run -d \
  --name redis-test \
  -p 6379:6379 \
  redis:7-alpine
```

### 2. Redis 연결 테스트

```bash
# Redis CLI로 접속
redis-cli ping
# 응답: PONG

# 비밀번호 설정된 경우
redis-cli -a your_password ping
```

### 3. 애플리케이션 테스트

**.env 설정**:
```bash
USE_REDIS_SESSION=true
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=
REDIS_DB=0
SESSION_TTL=3600
```

**서버 시작**:
```bash
uv run uvicorn backend.main:app --reload
```

**로그 확인**:
```
✅ Redis connection established (TTL: 3600s)
🚀 Using RedisConversationStore for session management
```

**세션 데이터 확인**:
```bash
# Redis에 저장된 모든 세션 키 확인
redis-cli KEYS "session:*"

# 특정 세션 데이터 조회
redis-cli GET "session:123e4567-e89b-12d3-a456-426614174000"

# 세션 TTL 확인
redis-cli TTL "session:123e4567-e89b-12d3-a456-426614174000"
```

### 4. 자동 테스트 실행

```bash
# 빠른 검증 테스트
uv run python scripts/quick/test_session_quick.py

# Pytest 전체 테스트 (Redis 실행 중이어야 함)
uv run pytest tests/test_session_store.py -v
```

---

## 마이그레이션 가이드

### InMemory → Redis 전환 절차

#### Step 1: Redis 서버 준비

클라우드 서비스 또는 로컬 Redis 서버를 준비합니다.

#### Step 2: 환경 변수 업데이트

```bash
# .env 파일 수정
USE_REDIS_SESSION=true
REDIS_URL=redis://your_redis_url  # 또는 개별 파라미터 설정
```

#### Step 3: 서버 재시작

```bash
# 서버 종료 (기존 InMemory 세션은 모두 손실됨)
# Ctrl+C

# 서버 시작
uv run uvicorn backend.main:app --reload
```

#### Step 4: 로그 확인

성공 시:
```
✅ Redis connection established (TTL: 3600s)
🚀 Using RedisConversationStore for session management
```

실패 시 (자동 폴백):
```
❌ Redis connection failed: [Errno 61] Connection refused
⚠️ Failed to initialize Redis: ...
🔄 Falling back to InMemoryConversationStore
💾 Using InMemoryConversationStore (development mode)
```

### 롤백 절차

Redis에 문제가 생긴 경우:

```bash
# .env 파일 수정
USE_REDIS_SESSION=false

# 서버 재시작
uv run uvicorn backend.main:app --reload
```

자동 폴백 기능이 있어서 Redis 연결 실패 시 자동으로 InMemory로 전환됩니다.

---

## 문제 해결

### Redis 연결 실패

#### 증상
```
❌ Redis connection failed: [Errno 61] Connection refused
🔄 Falling back to InMemoryConversationStore
```

#### 해결 방법

1. **Redis 서버 상태 확인**:
   ```bash
   redis-cli ping
   # 또는
   docker ps | grep redis
   ```

2. **연결 정보 확인**:
   - `REDIS_HOST`, `REDIS_PORT` 값이 올바른지 확인
   - 비밀번호가 필요한 경우 `REDIS_PASSWORD` 설정 확인

3. **방화벽 확인**:
   - Redis 포트(기본 6379)가 열려있는지 확인

### TTL 관련 문제

#### 증상
세션이 너무 빨리 만료되거나, 만료되지 않음

#### 해결 방법

**TTL 확인**:
```bash
redis-cli TTL "session:your_session_id"
# -2: 키가 존재하지 않음
# -1: TTL이 설정되지 않음 (영구)
# 양수: 남은 시간 (초)
```

**TTL 재설정**:
```bash
# .env 파일
SESSION_TTL=7200  # 2시간으로 변경
```

### JSON 직렬화 오류

#### 증상
```
JSON encode error for session xxx: Object of type datetime is not JSON serializable
```

#### 해결 방법

세션 상태에 datetime, numpy array 등 직렬화 불가능한 객체가 포함되어 있습니다.

**수정 전**:
```python
state = {
    "timestamp": datetime.now()  # ❌ 직렬화 불가
}
```

**수정 후**:
```python
import time
state = {
    "timestamp": time.time()  # ✅ float로 저장
}
```

### 메모리 부족

#### 증상
Redis 메모리가 부족하여 새 세션을 저장할 수 없음

#### 해결 방법

**Redis 메모리 사용량 확인**:
```bash
redis-cli INFO memory
```

**해결책**:
1. **TTL 단축**: SESSION_TTL을 줄여서 세션이 빨리 만료되도록 설정
2. **수동 정리**: 오래된 세션 수동 삭제
   ```bash
   redis-cli DEL "session:old_session_id"
   ```
3. **Redis 메모리 확장**: 클라우드 서비스 플랜 업그레이드 또는 서버 메모리 증설

---

## API 참조

### RedisConversationStore 메서드

| 메서드 | 설명 | 예시 |
|--------|------|------|
| `get_state(session_id)` | 세션 상태 조회 | `store.get_state("abc-123")` |
| `save_state(session_id, state)` | 세션 상태 저장 (TTL 자동 설정) | `store.save_state("abc-123", {...})` |
| `delete_state(session_id)` | 세션 삭제 | `store.delete_state("abc-123")` |
| `create_new_session_id()` | 새 세션 ID 생성 | `sid = store.create_new_session_id()` |
| `extend_ttl(session_id)` | TTL 연장 (기존 TTL로 재설정) | `store.extend_ttl("abc-123")` |
| `get_all_session_ids()` | 모든 활성 세션 ID 조회 | `ids = store.get_all_session_ids()` |

### Factory 함수

```python
from backend.agents.orchestrator.session_store import create_conversation_store

# 환경 변수에 따라 자동으로 InMemory 또는 Redis 선택
store = create_conversation_store()
```

---

## 참고 자료

### 관련 파일

| 파일 | 설명 |
|------|------|
| `backend/agents/orchestrator/session_store.py` | 세션 스토어 구현 |
| `backend/agents/orchestrator/nodes.py` | 오케스트레이터 노드 (스토어 사용) |
| `backend/config.py` | Redis 설정 |
| `tests/test_session_store.py` | 단위 테스트 |
| `scripts/quick/test_session_quick.py` | 빠른 검증 테스트 |

### 외부 문서

- [Redis Documentation](https://redis.io/docs/)
- [redis-py Documentation](https://redis-py.readthedocs.io/)
- [Redis Cloud Free Tier](https://redis.com/try-free/)

---

**문서 버전**: 1.0
**최종 수정**: 2026-02-16
**작성자**: Task #7 완료 시점
