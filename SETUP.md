# Quick Setup Guide

## 1) Python 의존성 설치

```bash
uv sync
```

## 2) 환경변수 설정

`.env` 파일에 최소 `UPSTAGE_API_KEY`를 설정하세요.

```env
UPSTAGE_API_KEY=your_actual_api_key_here
```

## 3) 백엔드 실행 (FastAPI)

```bash
uv run uvicorn backend.main:app --reload
```

확인 URL:
- API: http://localhost:8000
- Swagger: http://localhost:8000/docs

## 4) 프론트엔드 실행 (React + Vite)

```bash
cd frontend
npm install
npm run dev
```

확인 URL:
- React UI: http://localhost:3000

`VITE_API_BASE_URL`를 지정하지 않으면 기본값 `http://localhost:8000/api`를 사용합니다.

## 5) 기본 동작 테스트

### Health Check

```bash
curl http://localhost:8000/health
```

예상 응답:

```json
{"status":"healthy"}
```

### Chat API Test

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"session_id":"manual-test-session","message":"안녕하세요","context":{}}'
```

## 6) 체크리스트

- [ ] `.env` 설정 완료
- [ ] FastAPI 서버 실행 확인 (`:8000`)
- [ ] React 프론트 실행 확인 (`:3000`)
- [ ] `/api/chat` 호출 확인
