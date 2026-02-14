# 시스템 전체 워크플로 분석 및 시각화

## 1. 시스템 전체 구조 설명

이 프로젝트는 Streamlit을 프론트엔드로, FastAPI를 백엔드로 사용하며, Upstage Solar LLM과 RAG(Retrieval-Augmented Generation) 시스템을 활용하여 에이전트 기반의 대화형 AI 코치를 구현합니다. 핵심은 `Orchestrator`가 사용자 질의를 받아 적절한 `Agent`로 라우팅하고, Agent는 RAG를 통해 관련 지식을 검색하여 최종 응답 또는 보고서를 생성하는 구조입니다.

## 2. Orchestrator 중심 데이터 흐름

`Orchestrator`는 시스템의 두뇌 역할을 합니다. 사용자 입력이 들어오면 `session_id`를 기반으로 대화 상태를 관리하며, 다음의 우선순위에 따라 적절한 Agent를 식별하고 호출합니다.

1.  **활성 Agent 우선**: 현재 세션에서 `analysis_in_progress` 상태인 Agent(예: RiskManagingAgent)가 있다면 해당 Agent로 계속 라우팅합니다.
2.  **프론트엔드 컨텍스트**: 프론트엔드에서 `context["mode"]`를 통해 특정 Agent를 지정할 수 있습니다.
3.  **트리거 단어 감지**: 미리 정의된 키워드(예: "실수", "클레임", "리스크" 등)가 사용자 입력에 포함되어 있는지 확인합니다. (현재 `RiskManagingAgent`에만 설정됨)
4.  **의미론적 유사성**: `SimilarityEngine`을 사용하여 사용자 입력이 특정 Agent의 도메인과 의미적으로 유사한지 판단합니다. (현재 `RiskManagingAgent`에만 설정됨)
5.  **기본 Agent**: 위 조건에 해당하지 않으면 `DefaultChatAgent`로 폴백합니다.

선택된 Agent는 사용자 입력과 대화 이력을 받아 비즈니스 로직을 수행하고, `Orchestrator`에게 응답과 업데이트된 상태(예: `analysis_in_progress` 플래그)를 반환합니다. `Orchestrator`는 이를 세션 저장소에 저장하고, 최종 응답을 FastAPI를 통해 프론트엔드로 전달합니다.

## 3. Agent 호출 구조

현재 `orchestrator.py`에 명시적으로 활성화된 사용자 정의 Agent는 `RiskManagingAgent`뿐입니다. `QuizAgent`, `EmailAgent`, `MistakeAgent`, `CEOAgent` 등 다른 Agent 클래스들은 주석 처리되어 있어 `Orchestrator`가 직접 호출하지 않습니다.

**`RiskManagingAgent` 호출 흐름:**
1.  사용자 입력이 `RiskManagingAgent`로 라우팅되면, `run()` 메서드가 실행됩니다.
2.  `trigger_detector`와 `similarity_engine`으로 리스크 관련 여부를 재확인합니다.
3.  `conversation_manager`를 통해 다중 턴 대화를 관리하며, 리스크 분석에 필요한 정보가 모두 수집되었는지(`analysis_ready`) 확인합니다. 정보가 불충분하면 추가 질문을 반환합니다.
4.  `analysis_ready` 상태가 되면, `rag_connector`를 호출하여 RAG 검색을 수행합니다.
    *   `rag_connector`는 `backend.rag.retriever.search()`를 사용하여 `ChromaDB` (벡터 스토어)에서 관련 문서를 검색합니다. 이 과정에서 `backend.rag.embedder.get_embedding`을 통해 사용자 쿼리가 임베딩됩니다.
    *   검색된 문서는 `rag_connector` 내부에서 리스크 관리 관련 `RAG_DATASETS`에 따라 필터링됩니다.
5.  `risk_engine`이 수집된 정보와 RAG 문서를 기반으로 리스크를 평가하고 스코어링합니다.
6.  `report_generator`가 리스크 평가 결과, 유사 사례, 증거 출처 등을 바탕으로 최종 `RiskReport` 객체를 생성합니다. 이 과정에서 LLM을 활용하여 보고서의 다양한 섹션(요약, 손실 시뮬레이션, 통제 미흡점 분석, 예방 전략, 신뢰도 점수)을 생성합니다.
7.  `RiskManagingAgent`는 생성된 `RiskReport` 객체를 JSON 문자열로 변환하여 `Orchestrator`에 반환하고, `analysis_in_progress` 플래그를 비활성화합니다.

## 4. FastAPI ↔ Streamlit ↔ Agent 연결

-   **Streamlit (frontend/app.py)**: 사용자의 요청을 받아 FastAPI 백엔드로 전달하고, 백엔드로부터 받은 응답을 화면에 렌더링합니다. "새로운 리스크 분석 시작"과 같은 버튼을 통해 대화를 초기화하거나 특정 Agent 로직을 트리거할 수 있습니다. `RiskManagingAgent`의 JSON 형식 보고서를 파싱하여 사용자 친화적인 형식으로 보여주는 역할을 수행합니다.
-   **FastAPI (backend/main.py, backend/api/routes.py)**: RESTful API 엔드포인트를 제공합니다. 특히 `/chat` 엔드포인트는 `ChatRequest`를 받아 `Orchestrator.run()`을 호출하고, `Orchestrator`의 결과를 `ChatResponse` 형태로 프론트엔드에 반환합니다. 이 외에 `/quiz/start`, `/quiz/answer` 등 퀴즈 관련 플레이스홀더 엔드포인트도 존재합니다.
-   **Agent (backend/agents/...)**: `Orchestrator`에 의해 호출되며, 실제 비즈니스 로직(RAG, LLM 호출, 데이터 처리 등)을 수행하고 구조화된 응답을 반환합니다.

## 5. 보고서 출력 흐름

1.  사용자가 `RiskManagingAgent`로 라우팅되고, 충분한 정보가 제공되어 `analysis_ready` 상태가 되면 리스크 분석이 시작됩니다.
2.  `RiskManagingAgent`는 `report_generator.py`의 `ReportGenerator`를 사용하여 상세한 `RiskReport` 객체를 생성합니다. 이 보고서는 `analysis_id`, `input_summary`, `risk_factors`, `loss_simulation` 등 다양한 구조화된 필드를 포함합니다.
3.  `RiskManagingAgent`는 생성된 `RiskReport` 객체를 `.model_dump_json()` 메서드를 통해 JSON 문자열로 직렬화합니다.
4.  이 JSON 문자열은 `Orchestrator`를 거쳐 FastAPI의 `/chat` 엔드포인트를 통해 `ChatResponse`의 `response` 필드에 담겨 Streamlit 프론트엔드로 전달됩니다.
5.  Streamlit 애플리케이션은 이 JSON 응답을 받아 파싱하고, 보고서의 내용을 사용자 친화적인 UI 형태로 화면에 표시합니다.

## 6. Mermaid graph

```mermaid
graph TD
    A[Streamlit Frontend] -->|User Input, Session ID| B(FastAPI /chat Endpoint);
    B -->|session_id, user_input, context| C(Orchestrator.run());
    C -->|Manage Session State, Route Intent| D{Agent Routing Logic};

    D -->|Active Agent, Frontend Context| E[RiskManagingAgent];
    D -->|Trigger Words, Semantic Similarity| E;
    D -->|Fallback| F[DefaultChatAgent];

    E -->|User Input, History| G(RiskManagingAgent.run());
    G --> H{ConversationManager<br/>(analysis_ready?)};
    H -->|No, needs more info| G;
    H -->|Yes, analysis_ready| I(RAGConnector);
    
    I -->|query, history| J(backend.rag.retriever.search());
    J --> K(backend.rag.embedder.get_embedding);
    K --> L(ChromaDB Vector Store);
    L --> J;
    J -->|Retrieved Docs| I;
    I -->|Filtered Docs| G;

    G --> M(RiskEngine);
    G --> N(ReportGenerator);
    N --> O(LLM Calls for Report Sections);
    O --> N;
    N -->|RiskReport Object| G;

    G -->|JSON RiskReport, analysis_in_progress=False| C;
    F -->|Chat Response| C;
    C -->|ChatResponse Object| B;
    B -->|Render Response| A;
```

---
