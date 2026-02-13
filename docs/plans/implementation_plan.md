# Implementation Plan: TradeOnboarding Agent

## Goal
Implement a production-ready **TradeOnboarding Agent** system based on `projectspec.md`. This AI-powered simulator helps new employees at shipping/import-export trading companies practice trade terminology, email writing, negotiation, CEO reporting, and mistake prevention through interactive chat-based learning.

## User Review Required

> [!IMPORTANT]
> **Tech Stack Decisions**
> - **LLM**: Upstage Solar API (solar-pro-preview-240910)
> - **Embedding**: Upstage Solar Embedding (solar-embedding-1-large)
> - **Vector DB**: Using FAISS (local) for MVP - no external API required
> - **Tracing**: LangSmith for monitoring and debugging
> - **Agent Framework**: LangGraph with LangSmith integration

> [!WARNING]
> **Data Structure**
> The dummy data in `dummydata1.md` and `dummydata2.md` is semi-structured. I will create a parser to convert this into:
> 1. Structured JSON for database storage
> 2. Embedded vectors for RAG retrieval (using Solar Embedding)
> 3. Prompt templates for each agent

---

## Proposed Changes

### Component 1: Project Structure & Initialization

#### [NEW] [trade-ai-agent/](file:///d:/01.%20study/01.sesac_upstage_ai/07.7주차/00.project/수정/온보딩교육ai/trade-ai-agent/)
Create the complete project structure:

```
trade-ai-agent/
├── frontend/                    # Next.js 14 App
│   ├── app/
│   │   ├── page.tsx            # Landing/Login
│   │   ├── chat/page.tsx       # Main Chat Interface
│   │   ├── quiz/page.tsx       # Quiz Dashboard
│   │   └── dashboard/page.tsx  # Score Dashboard
│   ├── components/
│   │   ├── chat/
│   │   │   ├── ChatInterface.tsx
│   │   │   ├── MessageBubble.tsx
│   │   │   └── InputBox.tsx
│   │   ├── quiz/
│   │   │   ├── QuizCard.tsx
│   │   │   └── ScoreDisplay.tsx
│   │   └── dashboard/
│   │       ├── StatsCard.tsx
│   │       └── ProgressChart.tsx
│   └── lib/
│       └── api.ts              # API client
│
├── backend/                     # FastAPI Backend
│   ├── main.py                 # FastAPI entry point
│   ├── requirements.txt
│   │
│   ├── api/
│   │   ├── chat.py             # Chat endpoint
│   │   ├── quiz.py             # Quiz endpoint
│   │   ├── email.py            # Email coaching endpoint
│   │   └── health.py           # Health check
│   │
│   ├── agents/
│   │   ├── orchestrator.py     # Intent detection & routing
│   │   ├── quiz_agent.py       # Quiz generation
│   │   ├── email_agent.py      # Email coaching
│   │   ├── mistake_agent.py    # Mistake prediction
│   │   └── ceo_agent.py        # CEO simulation
│   │
│   ├── rag/
│   │   ├── retriever.py        # Vector search
│   │   ├── embeddings.py       # Embedding generation
│   │   └── context_builder.py  # Context assembly
│   │
│   ├── db/
│   │   ├── vector.py           # Pinecone client
│   │   ├── postgres.py         # PostgreSQL (mock for MVP)
│   │   └── redis.py            # Redis session (mock for MVP)
│   │
│   ├── prompts/
│   │   ├── quiz_prompt.txt
│   │   ├── email_prompt.txt
│   │   ├── ceo_prompt.txt
│   │   └── mistake_prompt.txt
│   │
│   └── utils/
│       └── data_parser.py      # Parse dummy data to JSON
│
└── dataset/                     # Processed Data
    ├── raw/
    │   ├── dummydata1.md       # Copy from source
    │   └── dummydata2.md       # Copy from source
    ├── company_domain.json
    ├── internal_process.json
    ├── mistakes.json
    ├── ceo_style.json
    ├── emails.json
    ├── negotiation.json
    ├── country_rules.json
    ├── claims.json
    ├── document_errors.json
    ├── trade_qa.json
    └── kpi.json
```

---

### Component 2: Data Processing Pipeline

#### [NEW] [data_parser.py](file:///d:/01.%20study/01.sesac_upstage_ai/07.7주차/00.project/수정/온보딩교육ai/trade-ai-agent/backend/utils/data_parser.py)

Parse `dummydata1.md` and `dummydata2.md` into structured JSON:

**From dummydata1.md:**
- `company_domain.json` (20 items, 6 fields)
- `internal_process.json` (20 items, 5 fields)
- `mistakes.json` (20 items, 5 fields)
- `ceo_style.json` (20 items, 4 fields)
- `emails.json` (20 items, 4 fields)

**From dummydata2.md:**
- `emails.json` (append 20 more)
- `mistakes.json` (append 20 more)
- `ceo_style.json` (append 20 more)
- `country_rules.json` (20 items)
- `negotiation.json` (20 items)
- `claims.json` (20 items)
- `document_errors.json` (20 items)
- `trade_qa.json` (20 items)
- `kpi.json` (20 items)

Each JSON will have a structure like:
```json
[
  {
    "id": 1,
    "category": "company_domain",
    "content": "BL (Bill of Lading) - 선하증권...",
    "metadata": {...}
  }
]
```

#### [NEW] [embeddings.py](file:///d:/01.%20study/01.sesac_upstage_ai/07.7주차/00.project/수정/온보딩교육ai/trade-ai-agent/backend/rag/embeddings.py)

Generate embeddings for all JSON data and store in FAISS:
- Use Upstage Solar `solar-embedding-1-large`
- Create FAISS index per category
- Store metadata for filtering

---

### Component 3: Backend - Agent System

#### [NEW] [orchestrator.py](file:///d:/01.%20study/01.sesac_upstage_ai/07.7주차/00.project/수정/온보딩교육ai/trade-ai-agent/backend/agents/orchestrator.py)

**Intent Detection & Agent Routing:**
```python
def route_agent(user_input: str) -> str:
    """
    Detect intent and route to appropriate agent
    
    Rules:
    - "메일" or "email" → email_agent
    - "퀴즈" or "quiz" → quiz_agent
    - "보고" or "report" or "대표" → ceo_agent
    - "실수" or "mistake" → mistake_agent
    - default → general_agent
    """
```

#### [NEW] [quiz_agent.py](file:///d:/01.%20study/01.sesac_upstage_ai/07.7주차/00.project/수정/온보딩교육ai/trade-ai-agent/backend/agents/quiz_agent.py)

**Quiz Generation Agent:**
- Retrieve from `company_domain.json` and `trade_qa.json`
- Generate multiple-choice or short-answer questions
- Score answers
- Provide explanations
- Track weak areas

#### [NEW] [email_agent.py](file:///d:/01.%20study/01.sesac_upstage_ai/07.7주차/00.project/수정/온보딩교육ai/trade-ai-agent/backend/agents/email_agent.py)

**Email Coaching Agent:**
- Retrieve from `emails.json` and `mistakes.json`
- Analyze tone, risk, accuracy
- Provide rewrite suggestions
- Highlight potential mistakes
- Apply CEO style preferences from `ceo_style.json`

#### [NEW] [mistake_agent.py](file:///d:/01.%20study/01.sesac_upstage_ai/07.7주차/00.project/수정/온보딩교육ai/trade-ai-agent/backend/agents/mistake_agent.py)

**Mistake Prediction Agent:**
- Retrieve from `mistakes.json` and `document_errors.json`
- Predict top 3 likely mistakes for given situation
- Provide prevention checklist
- Reference past cases

#### [NEW] [ceo_agent.py](file:///d:/01.%20study/01.sesac_upstage_ai/07.7주차/00.project/수정/온보딩교육ai/trade-ai-agent/backend/agents/ceo_agent.py)

**CEO Simulator Agent:**
- Retrieve from `ceo_style.json` and `kpi.json`
- Simulate CEO persona (risk-averse, detail-oriented)
- Ask tough business questions
- Evaluate reports
- Provide feedback

---

### Component 4: Backend - RAG System

#### [NEW] [retriever.py](file:///d:/01.%20study/01.sesac_upstage_ai/07.7주차/00.project/수정/온보딩교육ai/trade-ai-agent/backend/rag/retriever.py)

**Vector Retrieval:**
```python
def retrieve_context(query: str, category: str, top_k: int = 5):
    """
    1. Generate embedding for query using Solar Embedding
    2. Search FAISS index with category filter
    3. Return top-k relevant documents
    """
```

#### [NEW] [context_builder.py](file:///d:/01.%20study/01.sesac_upstage_ai/07.7주차/00.project/수정/온보딩교육ai/trade-ai-agent/backend/rag/context_builder.py)

**Context Assembly:**
```python
def build_prompt(query: str, docs: list, agent_type: str):
    """
    Assemble retrieved docs into LLM prompt
    Include agent-specific instructions
    """
```

---

### Component 5: Backend - API Endpoints

#### [NEW] [main.py](file:///d:/01.%20study/01.sesac_upstage_ai/07.7주차/00.project/수정/온보딩교육ai/trade-ai-agent/backend/main.py)

FastAPI application with CORS, endpoints:
- `POST /api/chat` - Main chat interface
- `POST /api/quiz/generate` - Generate quiz
- `POST /api/quiz/submit` - Submit answer
- `POST /api/email/coach` - Email coaching
- `GET /api/health` - Health check

---

### Component 6: Frontend - Next.js Application

#### [NEW] [ChatInterface.tsx](file:///d:/01.%20study/01.sesac_upstage_ai/07.7주차/00.project/수정/온보딩교육ai/trade-ai-agent/frontend/components/chat/ChatInterface.tsx)

**Main Chat UI:**
- Real-time message streaming
- Agent type indicator
- Message history
- Input with suggestions

#### [NEW] [QuizCard.tsx](file:///d:/01.%20study/01.sesac_upstage_ai/07.7주차/00.project/수정/온보딩교육ai/trade-ai-agent/frontend/components/quiz/QuizCard.tsx)

**Quiz Interface:**
- Question display
- Answer input
- Immediate feedback
- Explanation panel

#### [NEW] [StatsCard.tsx](file:///d:/01.%20study/01.sesac_upstage_ai/07.7주차/00.project/수정/온보딩교육ai/trade-ai-agent/frontend/components/dashboard/StatsCard.tsx)

**Dashboard:**
- Quiz scores
- Weak areas
- Progress tracking
- Activity history

---

### Component 7: Deployment Configuration

#### [NEW] [vercel.json](file:///d:/01.%20study/01.sesac_upstage_ai/07.7주차/00.project/수정/온보딩교육ai/trade-ai-agent/frontend/vercel.json)
Frontend deployment config for Vercel

#### [NEW] [Dockerfile](file:///d:/01.%20study/01.sesac_upstage_ai/07.7주차/00.project/수정/온보딩교육ai/trade-ai-agent/backend/Dockerfile)
Backend containerization for Railway/Fly.io

#### [NEW] [.env.example](file:///d:/01.%20study/01.sesac_upstage_ai/07.7주차/00.project/수정/온보딩교육ai/trade-ai-agent/.env.example)
Environment variables template:
```
UPSTAGE_API_KEY=
LANGSMITH_API_KEY=
LANGSMITH_PROJECT=trade-onboarding-agent
DATABASE_URL=
REDIS_URL=
```

---

## Verification Plan

### Automated Tests
```bash
# Backend tests
cd backend
pytest tests/

# API health check
curl http://localhost:8000/api/health
```

### Manual Verification
1. **Data Processing**
   - Run `data_parser.py`
   - Verify JSON files in `dataset/`
   - Check embedding upload to Pinecone

2. **Backend Testing**
   - Start FastAPI: `uvicorn main:app --reload`
   - Test each agent endpoint
   - Verify RAG retrieval

3. **Frontend Testing**
   - Start Next.js: `npm run dev`
   - Test chat interface
   - Test quiz flow
   - Test email coaching
   - Test CEO simulator

4. **Integration Testing**
   - Complete user flow:
     1. Ask for quiz → Verify quiz generation
     2. Submit email → Verify coaching feedback
     3. Report to CEO → Verify CEO questions
     4. Ask about mistakes → Verify predictions

5. **Deployment Testing**
   - Deploy frontend to Vercel
   - Deploy backend to Railway
   - Test production endpoints
