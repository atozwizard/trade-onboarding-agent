# Task List for TradeOnboarding Agent

## Phase 1: Project Setup
- [x] Initialize Project Structure
    - [x] Create `trade-ai-agent` root directory
    - [x] Create `frontend/`, `backend/`, `dataset/` directories
    - [x] Copy `dummydata1.md` and `dummydata2.md` to `dataset/raw/`

## Phase 2: Data Processing
- [x] Data Parser Implementation
    - [x] Create `backend/utils/data_parser.py`
    - [x] Parse dummydata1.md → JSON files
        - [x] `company_domain.json` (20 items)
        - [x] `internal_process.json` (20 items)
        - [x] `mistakes.json` (20 items)
        - [x] `ceo_style.json` (20 items)
        - [x] `emails.json` (20 items)
    - [x] Parse dummydata2.md → JSON files
        - [x] Append to `emails.json` (20 more)
        - [x] Append to `mistakes.json` (20 more)
        - [x] Append to `ceo_style.json` (20 more)
        - [x] `country_rules.json` (20 items)
        - [x] `negotiation.json` (20 items)
        - [x] `claims.json` (20 items)
        - [x] `document_errors.json` (20 items)
        - [x] `trade_qa.json` (20 items)
        - [x] `kpi.json` (20 items)
    - [x] Run parser and verify all JSON files

## Phase 3: Backend - RAG System
- [x] Setup Backend Environment
    - [x] Create `backend/requirements.txt`
    - [ ] Create virtual environment
- [x] RAG Implementation
    - [x] Create `backend/rag/embeddings.py`
    - [x] Create `backend/rag/retriever.py`
    - [x] Create `backend/rag/context_builder.py`
    - [x] Create `backend/db/vector.py` (FAISS-based)
    - [ ] Generate embeddings for all JSON data
    - [ ] Build FAISS indexes

## Phase 4: Backend - Agent System
- [x] Agent Implementation
    - [x] Create `backend/agents/orchestrator.py` (Intent detection & routing)
    - [x] Create `backend/agents/quiz_agent.py`
    - [x] Create `backend/agents/email_agent.py`
    - [x] Create `backend/agents/mistake_agent.py`
    - [x] Create `backend/agents/ceo_agent.py`
- [ ] Prompt Templates
    - [ ] Create `backend/prompts/quiz_prompt.txt`
    - [ ] Create `backend/prompts/email_prompt.txt`
    - [ ] Create `backend/prompts/ceo_prompt.txt`
    - [ ] Create `backend/prompts/mistake_prompt.txt`

## Phase 5: Backend - API Layer
- [x] API Implementation
    - [x] Create `backend/main.py` (FastAPI app)
    - [x] Create `backend/api/chat.py`
    - [x] Create `backend/api/quiz.py`
    - [x] Create `backend/api/email.py`
    - [x] Create `backend/api/health.py`
    - [x] Setup CORS
- [x] Mock Database
    - [x] Create `backend/db/postgres.py` (mock)
    - [x] Create `backend/db/redis.py` (mock)

## Phase 6: Frontend - Next.js App
- [ ] Initialize Frontend
    - [ ] Create Next.js 14 app with TypeScript
    - [ ] Setup Tailwind CSS
    - [ ] Create folder structure
- [ ] Pages
    - [ ] Create `app/page.tsx` (Landing/Login)
    - [ ] Create `app/chat/page.tsx` (Main Chat)
    - [ ] Create `app/quiz/page.tsx` (Quiz Dashboard)
    - [ ] Create `app/dashboard/page.tsx` (Score Dashboard)
- [ ] Chat Components
    - [ ] Create `components/chat/ChatInterface.tsx`
    - [ ] Create `components/chat/MessageBubble.tsx`
    - [ ] Create `components/chat/InputBox.tsx`
- [ ] Quiz Components
    - [ ] Create `components/quiz/QuizCard.tsx`
    - [ ] Create `components/quiz/ScoreDisplay.tsx`
- [ ] Dashboard Components
    - [ ] Create `components/dashboard/StatsCard.tsx`
    - [ ] Create `components/dashboard/ProgressChart.tsx`
- [ ] API Integration
    - [ ] Create `lib/api.ts` (API client)

## Phase 7: Integration & Testing
- [ ] Backend Testing
    - [ ] Test data parser
    - [ ] Test RAG retrieval
    - [ ] Test each agent individually
    - [ ] Test API endpoints
- [ ] Frontend Testing
    - [ ] Test chat interface
    - [ ] Test quiz flow
    - [ ] Test email coaching
    - [ ] Test CEO simulator
- [ ] Integration Testing
    - [ ] Complete user flow test

## Phase 8: Deployment
- [ ] Deployment Configuration
    - [ ] Create `.env.example`
    - [ ] Create `frontend/vercel.json`
    - [ ] Create `backend/Dockerfile`
- [ ] Deploy
    - [ ] Deploy frontend to Vercel
    - [ ] Deploy backend to Railway/Fly.io
    - [ ] Configure environment variables
    - [ ] Test production endpoints
