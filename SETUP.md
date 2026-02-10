# 🚀 Quick Setup Guide (uv)

## 1. 환경 설정

### uv 설치 (아직 없다면)
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 의존성 설치
```bash
# 가상환경 생성 + 패키지 설치 (한 번에!)
uv sync
```

이 명령어는 자동으로:
- `.venv` 가상환경 생성
- `pyproject.toml`에 정의된 모든 패키지 설치
- `uv.lock` 파일 생성 (의존성 잠금)

### 환경변수 설정
`.env` 파일을 열고 API 키를 입력하세요:
```bash
UPSTAGE_API_KEY=your_actual_api_key_here
```

## 2. 서버 실행

### Backend (FastAPI)
uv run uvicorn backend.main:app --reload
```

서버 실행 후 확인:
- API: http://localhost:8000
- API 문서: http://localhost:8000/docs

### Frontend (Streamlit)
uv run streamlit run frontend/app.py
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
  -d '{"message": "안녕하세요", "context": {}}'
```

## 4. uv 주요 명령어

```bash
# 패키지 추가
uv add <package-name>

# 개발 패키지 추가
uv add --dev <package-name>

# 패키지 제거
uv remove <package-name>

# 의존성 업데이트
uv sync --upgrade

# Python 스크립트 실행
uv run python script.py

# 가상환경 직접 활성화 (선택사항)
source .venv/bin/activate  # Mac/Linux
```

## 5. 개발 체크리스트

- [x] uv 설치 완료
- [x] 의존성 설치 완료 (154 packages)
- [x] .venv 가상환경 생성됨
- [ ] .env 파일에 API 키 설정
- [ ] FastAPI 서버 실행 확인
- [ ] Streamlit UI 실행 확인

## 다음 단계

상세한 내용은 [README.md](README.md) 참고
