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
- **LLM**: Upstage Solar API (solar-pro-preview-240910)
- **Embedding**: Upstage Solar Embedding (solar-embedding-1-large)
- **Vector Store**: FAISS (local)
- **Agent Framework**: LangGraph
- **Tracing**: LangSmith

### Frontend
- **Framework**: Next.js 14
- **Language**: TypeScript
- **Styling**: Tailwind CSS

## 📁 Project Structure

```
trade-ai-agent/
├── backend/
│   ├── main.py                 # FastAPI application
│   ├── requirements.txt
│   ├── agents/                 # Agent implementations
│   │   ├── orchestrator.py
│   │   ├── quiz_agent.py
│   │   ├── email_agent.py
│   │   ├── mistake_agent.py
│   │   └── ceo_agent.py
│   ├── rag/                    # RAG system
│   │   ├── embeddings.py
│   │   ├── retriever.py
│   │   └── context_builder.py
│   ├── utils/
│   │   └── data_parser.py      # Data preprocessing
│   └── api/                    # API endpoints
│
├── dataset/                     # Processed data
│   ├── raw/                    # Original markdown files
│   ├── *.json                  # Structured JSON data
│   └── embeddings/             # FAISS indexes
│
└── frontend/                    # Next.js application
    └── (to be implemented)
```

## 🚀 Quick Start

### Prerequisites

- Python 3.9+
- Node.js 18+
- Upstage API Key
- LangSmith API Key (optional, for tracing)

### Backend Setup

1. **Clone and navigate to backend**
```bash
cd trade-ai-agent/backend
```

2. **Create virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Set up environment variables**
```bash
cp ../.env.example .env
# Edit .env and add your API keys:
# UPSTAGE_API_KEY=your_key_here
# LANGSMITH_API_KEY=your_key_here (optional)
```

5. **Process data and build embeddings**
```bash
# Parse dummy data to JSON
cd utils
python data_parser.py
cd ..

# Build FAISS indexes
cd rag
python retriever.py
cd ..
```

6. **Run the server**
```bash
uvicorn main:app --reload
```

The API will be available at `http://localhost:8000`

### API Documentation

Once the server is running, visit:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## 📡 API Endpoints

### Main Endpoints

- `POST /api/chat` - Main chat interface (auto-routes to appropriate agent)
- `POST /api/quiz/generate` - Generate a quiz
- `POST /api/email/coach` - Get email feedback
- `POST /api/mistake/predict` - Predict potential mistakes
- `POST /api/ceo/simulate` - Simulate CEO interaction
- `GET /api/health` - Health check
- `GET /api/agents` - List available agents

### Example Usage

**Chat Request:**
```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "BL에 대한 퀴즈를 내줘"
  }'
```

**Email Coaching:**
```bash
curl -X POST http://localhost:8000/api/email/coach \
  -H "Content-Type: application/json" \
  -d '{
    "email_draft": "Dear buyer, The shipment will be delayed."
  }'
```

## 🧪 Testing

### Test Individual Agents

```bash
# Test Quiz Agent
cd agents
python quiz_agent.py

# Test Email Agent
python email_agent.py

# Test Mistake Agent
python mistake_agent.py

# Test CEO Agent
python ceo_agent.py
```

### Test RAG System

```bash
cd rag
python retriever.py
python context_builder.py
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

## 📈 Future Enhancements

- [ ] Frontend implementation (Next.js)
- [ ] User authentication
- [ ] Progress tracking dashboard
- [ ] Real-time chat with WebSocket
- [ ] Multi-language support
- [ ] Integration with actual company data
- [ ] Mobile app

## 🤝 Contributing

This is an MVP project. Contributions are welcome!

## 📄 License

MIT License

## 👥 Authors

- AI Agent Development Team

## 🙏 Acknowledgments

- Upstage for Solar API
- LangChain for agent framework
- FastAPI for backend framework


 다음 단계:

.env 파일에 API 키 설정 필요 (UPSTAGE_API_KEY, LANGSMITH_API_KEY)
가상환경 생성 및 의존성 설치
FAISS 인덱스 빌드
백엔드 서버 실행 및 테스트