# 📝 로깅 시스템 가이드

## 개요

Trade Onboarding Agent는 프로덕션 환경에 적합한 로깅 시스템을 갖추고 있습니다.

### 주요 기능

- ✅ **날짜별 자동 로테이션**: 매일 자정에 새로운 로그 파일 생성
- ✅ **파일 크기 제한**: 10MB 초과 시 자동 백업
- ✅ **레벨별 파일 분리**: 전체 로그 / 에러 전용 / 디버그 (개발 환경만)
- ✅ **콘솔 + 파일 동시 출력**: 개발 중에도 편리하게 확인
- ✅ **상세한 포맷**: 타임스탬프, 레벨, 파일명, 함수명, 라인번호 포함
- ✅ **환경별 로그 레벨**: 개발(DEBUG), 프로덕션(INFO), 테스트(WARNING)

---

## 로그 파일 구조

```
logs/
├── trade_onboarding.log          # 전체 로그 (INFO 이상)
├── trade_onboarding.log.2026-02-11  # 전날 로그 (자동 백업)
├── trade_onboarding.log.2026-02-10
├── trade_onboarding_error.log    # 에러만 (ERROR 이상)
├── trade_onboarding_error.log.1  # 에러 백업 파일
└── trade_onboarding_debug.log    # 디버그 포함 (개발 환경만)
```

### 로그 파일 설명

| 파일 | 내용 | 로테이션 방식 | 보관 기간 |
|------|------|---------------|----------|
| `trade_onboarding.log` | 모든 로그 (INFO 이상) | 매일 자정 | 30일 |
| `trade_onboarding_error.log` | 에러만 (ERROR 이상) | 10MB 초과 시 | 최대 5개 파일 |
| `trade_onboarding_debug.log` | 디버그 포함 (개발 환경만) | 10MB 초과 시 | 최대 3개 파일 |

---

## 사용 방법

### 1. 앱 시작 시 로깅 초기화 (자동)

`backend/main.py`에서 자동으로 초기화됩니다:

```python
from backend.utils.logger import setup_logging, get_logger
from backend.config import get_settings

settings = get_settings()
setup_logging(environment=settings.environment, app_name="trade_onboarding")
logger = get_logger(__name__)
```

### 2. 코드에서 로깅 사용

```python
import logging

# 로거 가져오기
logger = logging.getLogger(__name__)

# 다양한 로그 레벨
logger.debug("변수 값 디버깅: x={}, y={}".format(x, y))
logger.info("사용자 요청 처리 시작: user_id={}".format(user_id))
logger.warning("벡터 DB 검색 결과 없음: query={}".format(query))
logger.error("RAG 검색 실패: {}".format(str(e)))

# 예외와 함께 로깅 (스택 트레이스 포함)
try:
    result = risky_operation()
except Exception as e:
    logger.error("작업 실패", exc_info=True)  # 스택 트레이스 포함
```

### 3. 로그 레벨 가이드

| 레벨 | 사용 시기 | 예시 |
|------|----------|------|
| `DEBUG` | 변수 값, 흐름 추적 (개발 중) | `logger.debug("query_embedding: {}")` |
| `INFO` | 정상 동작 기록 | `logger.info("서버 시작 완료")` |
| `WARNING` | 비정상이지만 처리 가능 | `logger.warning("캐시 미스, DB 재검색")` |
| `ERROR` | 처리 실패, 예외 발생 | `logger.error("RAG 검색 실패")` |
| `CRITICAL` | 치명적 오류 (거의 사용 안 함) | `logger.critical("DB 연결 불가")` |

---

## 로그 포맷

### 파일 로그 (상세)

```
2026-02-12 14:35:21 | INFO     | backend.main:startup_event:53 | 🚀 무역 온보딩 AI 코치 API 시작 중...
2026-02-12 14:35:22 | ERROR    | backend.rag.retriever:search:92 | 검색 실패: ChromaDB connection error
```

**포맷 설명**:
- `2026-02-12 14:35:21`: 타임스탬프
- `INFO`: 로그 레벨
- `backend.main`: 모듈명
- `startup_event`: 함수명
- `53`: 라인번호
- `🚀 무역 온보딩 AI 코치 API 시작 중...`: 메시지

### 콘솔 로그 (간단)

```
2026-02-12 14:35:21 | INFO     | 🚀 무역 온보딩 AI 코치 API 시작 중...
```

---

## 테스트

### 로깅 시스템 테스트

```bash
# 테스트 스크립트 실행
cd trade-onboarding-agent
uv run python backend/utils/test_logger.py

# 로그 파일 확인
ls -lh logs/
cat logs/test_trade_onboarding.log
cat logs/test_trade_onboarding_error.log
```

### 실시간 로그 모니터링

```bash
# 전체 로그 실시간 보기
tail -f logs/trade_onboarding.log

# 에러만 실시간 보기
tail -f logs/trade_onboarding_error.log

# 최근 100줄 보기
tail -n 100 logs/trade_onboarding.log
```

---

## 환경별 로그 레벨

환경 변수 `ENVIRONMENT`에 따라 로그 레벨이 자동 조정됩니다:

| 환경 | 로그 레벨 | 콘솔 출력 | 파일 저장 | 디버그 파일 |
|------|----------|----------|----------|------------|
| `development` | `DEBUG` | ✅ | ✅ | ✅ |
| `production` | `INFO` | ✅ | ✅ | ❌ |
| `test` | `WARNING` | ✅ | ✅ | ❌ |

`.env` 파일에서 설정:

```bash
# 개발 환경 (디버그 포함)
ENVIRONMENT=development

# 프로덕션 환경 (INFO 이상만)
ENVIRONMENT=production
```

---

## 외부 라이브러리 로그 제어

노이즈를 줄이기 위해 외부 라이브러리의 로그 레벨을 조정합니다:

```python
# backend/utils/logger.py에서 자동 설정됨
logging.getLogger("uvicorn").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("chromadb").setLevel(logging.WARNING)
```

**변경하려면** `backend/utils/logger.py`의 `setup_logging()` 함수 하단 수정:

```python
# 특정 라이브러리의 디버그 로그를 보고 싶을 때
logging.getLogger("chromadb").setLevel(logging.DEBUG)
```

---

## 모범 사례

### ✅ 좋은 예시

```python
# 1. 구체적인 컨텍스트 포함
logger.info(f"Quiz generated: difficulty={difficulty}, question_count={len(questions)}")

# 2. 예외와 함께 로깅 (스택 트레이스 포함)
try:
    docs = retriever.search(query, k=5)
except RetrievalError as e:
    logger.error(f"RAG 검색 실패: query='{query}'", exc_info=True)
    raise

# 3. 디버그 로그는 개발 중에만 의미 있는 정보
logger.debug(f"Query embedding: {query_embedding[:10]}...")  # 벡터 일부만 출력

# 4. 사용자 액션 추적
logger.info(f"User request: agent=quiz, session_id={session_id}")
```

### ❌ 나쁜 예시

```python
# 1. 너무 일반적인 메시지
logger.info("success")  # ❌ 무엇이 성공했는지 불명확

# 2. 민감 정보 로깅
logger.info(f"API Key: {api_key}")  # ❌ 보안 위험

# 3. 불필요한 로그
logger.debug("Entering function")  # ❌ 함수 진입/종료는 불필요
logger.debug("Exiting function")

# 4. 반복문 내 과도한 로깅
for item in items:
    logger.info(f"Processing {item}")  # ❌ 수천 개면 로그 파일 폭발
```

---

## 문제 해결

### 로그 파일이 생성되지 않음

**원인**: `logs/` 디렉토리 쓰기 권한 없음

**해결**:
```bash
mkdir -p logs
chmod 755 logs
```

### 로그 파일 크기가 너무 커짐

**원인**: 디버그 로그가 너무 많이 출력됨

**해결**:
1. `.env`에서 `ENVIRONMENT=production` 설정 (INFO 이상만 기록)
2. 또는 `backend/utils/logger.py`에서 백업 파일 개수 조정:
   ```python
   backupCount=3  # 기본값 5 → 3으로 축소
   ```

### 특정 모듈의 로그만 보고 싶음

```python
# 특정 모듈 로거만 DEBUG 레벨로 설정
logging.getLogger("backend.agents.quiz_agent").setLevel(logging.DEBUG)
```

---

## 추가 기능 (향후 확장 가능)

### JSON 로그 포맷 (ELK Stack 연동용)

```python
# backend/utils/logger.py에 추가
import json_log_formatter

json_formatter = json_log_formatter.JSONFormatter()
json_handler = logging.FileHandler("logs/trade_onboarding.json")
json_handler.setFormatter(json_formatter)
root_logger.addHandler(json_handler)
```

### Sentry 연동 (에러 알림)

```python
# backend/utils/logger.py에 추가
import sentry_sdk
from sentry_sdk.integrations.logging import LoggingIntegration

sentry_sdk.init(
    dsn="YOUR_SENTRY_DSN",
    integrations=[LoggingIntegration(level=logging.ERROR)]
)
```

---

## 참고 자료

- [Python Logging 공식 문서](https://docs.python.org/3/library/logging.html)
- [Logging Best Practices](https://docs.python-guide.org/writing/logging/)
- [12-Factor App - Logs](https://12factor.net/logs)

---

**마지막 업데이트**: 2026-02-12
