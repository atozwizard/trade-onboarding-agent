# TradeOnboarding Agent 🚢

AI-powered onboarding simulator for trading company new employees.

## 📋 Overview

TradeOnboarding Agent는 선박 기반 수출입 무역회사 신입사원의 실무 적응을 돕는 AI 에이전트 기반 온보딩 시뮬레이터입니다.

### Key Features

- **🎯 Quiz Agent**: 무역 용어 및 프로세스 퀴즈 생성 및 평가
- **✉️ Email Coach Agent**: 이메일 작성 피드백 및 코칭
- **⚠️ Mistake Predictor Agent**: 상황별 실수 예측 및 예방 가이드
- **👔 CEO Simulator Agent**: 대표 보고 연습 시뮬레이션

## 🛠 Tech Stack

### Backend
- **Framework**: FastAPI
- **LLM**: Upstage Solar API
- **Embedding**: Upstage Solar Embedding
- **Vector Store**: ChromaDB
- **Agent Framework**: LangChain
- **Package Manager**: uv (fast Python package manager)

### Frontend
- **Framework**: Streamlit
- **Language**: Python

## 📁 Project Structure

```
trade-onboarding-agent/
├── backend/
│   ├── main.py                 # FastAPI application
│   ├── config.py               # Environment configuration
│   ├── agents/                 # Agent implementations
│   │   ├── orchestrator.py     # Intent routing
│   │   ├── quiz_agent.py       # #1 Quiz learning
│   │   ├── email_agent.py      # #2 Email coaching
│   │   ├── mistake_agent.py    # #3 Mistake prediction
│   │   └── ceo_agent.py        # #4 CEO simulation
│   ├── rag/                    # RAG system
│   │   ├── retriever.py        # Vector search
│   │   └── data/               # Embeddings
│   ├── prompts/                # LLM prompts
│   │   ├── quiz_prompt.txt
│   │   ├── email_prompt.txt
│   │   ├── orchestrator.txt
│   │   ├── mistake_prompt.txt
│   │   └── ceo_prompt.txt
│   └── api/
│       └── routes.py           # API endpoints
│
├── frontend/
│   └── app.py                  # Streamlit UI
│
├── dataset/                    # Structured data
│   ├── raw/                    # Original markdown
│   └── *.json                  # 200+ data points
│
├── pyproject.toml              # uv project config
├── uv.lock                     # Dependency lock file
└── .env                        # Environment variables
```

## 🚀 Quick Start

### Prerequisites

- **Python 3.11+**
- **uv** (fast Python package manager)
- **Upstage API Key**
- LangSmith API Key (optional, for tracing)

### Installation

#### 1. Install uv (if not installed)
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

#### 2. Clone repository
```bash
git clone <repository-url>
cd trade-onboarding-agent
```

#### 3. Install dependencies
```bash
# This creates .venv and installs all packages
uv sync
```

#### 4. Set up environment variables
```bash
# Copy example and edit
cp .env.example .env

# Add your API keys to .env:
# UPSTAGE_API_KEY=your_actual_api_key_here
```

### Running the Application

#### Backend (FastAPI)
```bash
uv run uvicorn backend.main:app --reload
```

The API will be available at:
- API: `http://localhost:8000`
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

#### Frontend (Streamlit)
Open a new terminal and run:
```bash
uv run streamlit run frontend/app.py
```

The UI will be available at `http://localhost:8501`

## 📡 API Endpoints

### Main Endpoints

- `GET /` - Root endpoint (health check)
- `GET /health` - Health check
- `POST /api/chat` - Main chat interface (auto-routes to appropriate agent)
- `POST /api/quiz/start` - Start a new quiz session
- `POST /api/quiz/answer` - Submit quiz answer

### Example Usage

**Health Check:**
```bash
curl http://localhost:8000/health
```

**Chat Request:**
```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "물류 퀴즈 풀고 싶어",
    "context": {"mode": "quiz"}
  }'
```

**Quiz Start:**
```bash
curl -X POST "http://localhost:8000/api/quiz/start?topic=BL&difficulty=easy"
```

## 🧪 Development

### Adding New Packages

```bash
# Add a regular dependency
uv add <package-name>

# Add a development dependency
uv add --dev <package-name>
```

### Running Tests

```bash
# Run with pytest (when implemented)
uv run pytest
```

### Code Formatting

```bash
# Format with black
uv run black backend/ frontend/

# Lint with ruff
uv run ruff check backend/ frontend/
```

## 📊 Data

The system uses structured data from two sources:

### dummydata1.md
- Company domain knowledge (20 items)
- Internal processes (20 items)
- Mistake cases (20 items)
- CEO decision style (20 items)
- Communication examples (20 items)

### dummydata2.md
- Email logs (20 items)
- Additional mistakes (20 items)
- CEO style (20 items)
- Country-specific rules (20 items)
- Negotiation cases (20 items)
- Claims (20 items)
- Document errors (20 items)
- Trade Q&A (20 items)
- KPI data (20 items)
- Quiz samples (20 items)

Total: **200+ structured data points**

## 🔧 Configuration

### Environment Variables

```env
# Upstage Solar API
UPSTAGE_API_KEY=your_upstage_api_key

# LangSmith (optional)
LANGSMITH_API_KEY=your_langsmith_api_key
LANGSMITH_PROJECT=trade-onboarding-agent
LANGSMITH_TRACING=true

# Application
ENVIRONMENT=development
DEBUG=true
```

## 🎯 Agent Routing Logic

The orchestrator automatically detects intent and routes to the appropriate agent:

- **"퀴즈", "quiz", "문제"** → Quiz Agent
- **"메일", "email", "이메일"** → Email Agent
- **"보고", "대표", "CEO"** → CEO Simulator
- **"실수", "mistake", "주의"** → Mistake Predictor
- **Default** → General Q&A

## 📈 Development Roadmap

### Day 1 오전 (완료)
- [x] 프로젝트 구조 생성
- [x] FastAPI 기본 서버 세팅
- [x] Streamlit 기본 UI 세팅
- [x] uv 기반 패키지 관리

### Day 1 오후 ~ Day 3 오전
- [ ] #1 퀴즈 학습 기능 (Quiz Agent)
- [ ] #2 이메일 코칭 기능 (Email Agent)
- [ ] #3 실수 예측 기능 (Mistake Agent)
- [ ] #4 대표 시뮬레이션 기능 (CEO Agent)

### Day 3 오후
- [ ] 통합 연동 (Orchestrator)
- [ ] RAG 시스템 구현
- [ ] ChromaDB 세팅

### Day 4 오전
- [ ] 대시보드 구현
- [ ] 최종 테스트

### Day 4 오후
- [ ] 배포
- [ ] 발표 준비

## 🔧 Troubleshooting

### Common Issues

**uv not found:**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.bashrc  # or ~/.zshrc
```

**Import errors:**
```bash
# Make sure you're using uv run
uv run python backend/main.py
```

**Environment variables not loaded:**
```bash
# Check .env file exists and has correct values
cat .env
```

## 📄 License

MIT License

## 🙏 Acknowledgments

- Upstage for Solar API
- LangChain for agent framework
- FastAPI for backend framework
- Streamlit for frontend framework