# 🚀 Quick Setup Guide

## 1. 환경 설정

### 가상환경 생성 및 활성화
```bash
python -m venv venv
source venv/bin/activate  # Mac/Linux
# or
venv\Scripts\activate  # Windows
```

### 패키지 설치
```bash
pip install -r requirements.txt
```

### 환경변수 설정
`.env` 파일을 열고 API 키를 입력하세요:
```bash
UPSTAGE_API_KEY=your_actual_api_key_here
```

## 2. 서버 실행

### Backend (FastAPI)
```bash
./run_backend.sh
# or
python -m uvicorn backend.main:app --reload
```

서버 실행 후 확인:
- API: http://localhost:8000
- API 문서: http://localhost:8000/docs

### Frontend (Streamlit)
```bash
./run_frontend.sh
# or
streamlit run frontend/app.py
```

프론트엔드 확인:
- Streamlit UI: http://localhost:8501

## 3. 테스트

### API Health Check
```bash
curl http://localhost:8000/health
```

예상 응답:
```json
{"status": "healthy"}
```

### Chat API Test
```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "안녕하세요"}'
```

## 4. 개발 체크리스트

- [ ] FastAPI 서버 실행됨 (`localhost:8000`)
- [ ] Streamlit 실행됨 (`localhost:8501`)
- [ ] API 문서 확인 (`localhost:8000/docs`)
- [ ] 채팅 UI에서 메시지 전송 가능
- [ ] .env 파일에 API 키 설정 완료

## 다음 단계

1. RAG 시스템 구현 (`backend/rag/retriever.py`)
2. 오케스트레이터 구현 (`backend/agents/orchestrator.py`)
3. 각 에이전트 구현 (#1~#4)
4. 프롬프트 작성 (`backend/prompts/*.txt`)
