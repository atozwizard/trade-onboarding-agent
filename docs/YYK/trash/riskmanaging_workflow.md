# riskmanaging_agent 워크플로

이 문서는 `riskmanaging_agent`의 내부 워크플로를 상세히 설명하고 시각화합니다.

## 1. 입력 → 처리 → 출력 흐름

`riskmanaging_agent`는 사용자의 질문과 대화 이력을 입력받아 리스크 분석을 수행하고, 최종적으로 구조화된 리스크 보고서를 JSON 형태로 출력합니다.

**입력:**
-   `user_input`: 현재 사용자 메시지 (e.g., "선적 지연 발생, 페널티 조항 있습니다.")
-   `conversation_history`: 이전 대화 턴의 목록 (Orchestrator에 의해 관리됨)
-   `analysis_in_progress`: 현재 리스크 분석 세션이 진행 중인지 여부를 나타내는 플래그 (Orchestrator에 의해 관리됨)
-   `context`: 프론트엔드로부터의 추가 컨텍스트 (예: 특정 모드 전환 요청)

**처리 (내부 판단 단계):**

1.  **초기 검토 및 활성화**:
    *   `trigger_detector`와 `similarity_engine`을 사용하여 `user_input`이 리스크 관리 관련 내용인지 확인합니다.
    *   이전 턴에 `analysis_in_progress` 플래그가 True였다면, 현재 턴에도 리스크 분석을 계속 진행합니다.
    *   만약 리스크 관련 트리거/유사성도 없고, `analysis_in_progress`도 False라면, `riskmanaging_agent`는 요청을 처리하지 않고 Orchestrator가 `DefaultChatAgent`로 폴백하도록 허용합니다.

2.  **대화 관리 및 정보 수집 (`conversation_manager`)**:
    *   사용자 입력과 대화 이력을 기반으로 `conversation_manager`가 현재까지의 대화 진행 상황(`conversation_status`)을 평가합니다.
    *   `analysis_ready` 플래그를 통해 리스크 분석에 필요한 정보가 충분히 수집되었는지 판단합니다.
    *   정보가 불충분할 경우, `conversation_manager`는 LLM을 사용하여 사용자에게 필요한 추가 질문(`follow_up_questions`)을 생성하여 반환하고, `analysis_in_progress`를 유지합니다.

3.  **RAG 기반 정보 검색 (`rag_connector`)**:
    *   `analysis_ready`가 True이면, `rag_connector`를 사용하여 `full_query_context`(현재 쿼리 + 대화 이력)에 대한 관련 문서를 검색합니다.
    *   `rag_connector`는 `backend.rag.retriever.search`를 호출하고, 검색 결과를 `riskmanaging` 도메인에 특화된 `RAG_DATASETS`로 필터링합니다.
    *   검색된 문서에서 유사 사례(`similar_cases`)와 증거 출처(`evidence_sources`)를 추출합니다.

4.  **리스크 평가 (`risk_engine`)**:
    *   사용자 입력과 RAG를 통해 검색된 문서를 바탕으로 `risk_engine`이 리스크 요인(`risk_factors`), 전반적인 리스크 수준(`overall_risk_level`), 평가(`overall_assessment`) 등을 포함한 `RiskScoring`을 수행합니다. 이 과정에서 LLM을 활용하여 상세한 평가를 생성합니다.

5.  **보고서 생성 (`report_generator`)**:
    *   `report_generator`는 `agent_input`, `RiskScoring` 결과, `similar_cases`, `evidence_sources`, `rag_documents` 등을 종합하여 최종 `RiskReport` 객체를 생성합니다.
    *   보고서 생성 과정에서 LLM을 여러 번 호출하여 `input_summary`, `loss_simulation_qualitative`, `control_gap_analysis`, `prevention_strategy`, `confidence_score` 등 각 섹션의 내용을 풍부하게 채웁니다.

**출력:**
-   `RiskManagingAgentResponse`:
    *   `response`: `RiskReport` 객체가 JSON 문자열로 직렬화된 형태.
    *   `agent_type`: "riskmanaging"
    *   `metadata`: `triggered`, `similar`, `final_report_id` 등의 정보 포함.
-   `conversation_history`: 업데이트된 대화 이력 (보고서 생성 후에는 초기화됨).
-   `analysis_in_progress`: `False` (보고서 생성 완료 후 리스크 분석 세션 종료).

## 2. 참조 데이터

`riskmanaging_agent`는 다음 데이터를 참조하고 활용합니다:

-   **사용자 입력/대화 이력**: `user_input`, `conversation_history`는 `conversation_manager`의 정보 수집 및 `risk_engine`의 리스크 평가의 핵심 기반이 됩니다.
-   **RAG 데이터셋**: `rag_connector`는 `backend/rag/retriever.search`를 통해 ChromaDB에 저장된 벡터화된 지식 베이스를 참조합니다. 특히 `backend/agents/riskmanaging/config.py`에 정의된 `RAG_DATASETS` (예: `claims.json`, `mistakes.json`, `country_rules.json` 등)에 해당하는 문서들만 필터링하여 리스크 관리에 특화된 정보를 사용합니다.
-   **LLM (Upstage Solar)**: `conversation_manager`, `risk_engine`, `report_generator` 내에서 사용자 질의 이해, 추가 질문 생성, 리스크 평가, 보고서 섹션별 콘텐츠 생성 등 복잡한 추론 및 텍스트 생성을 위해 사용됩니다.
-   **사전 정의된 프롬프트**: `backend/agents/riskmanaging/prompt_loader.py`에 정의된 시스템 프롬프트 및 각 기능(요약, 시뮬레이션, 분석, 전략 등)별 프롬프트 템플릿을 사용하여 LLM의 동작을 제어하고 일관된 응답을 유도합니다.

## 3. agent 의사결정 흐름

`riskmanaging_agent`의 의사결정은 크게 '정보 수집 단계'와 '분석 및 보고 단계'로 나눌 수 있습니다.

-   **정보 수집 단계**: `conversation_manager`가 핵심 역할을 하며, 필요한 정보가 모두 수집될 때까지 사용자에게 추가 질문을 반복적으로 던집니다. 이는 `analysis_in_progress` 플래그를 `True`로 유지함으로써 Orchestrator가 다음 턴에도 `riskmanaging_agent`로 계속 라우팅하도록 합니다.
-   **분석 및 보고 단계**: `analysis_ready`가 `True`가 되면, `rag_connector`, `risk_engine`, `report_generator` 모듈이 순차적으로 호출되어 최종 보고서를 생성하고, `analysis_in_progress`를 `False`로 설정하여 세션을 종료합니다.

## 4. Mermaid graph
```mermaid
graph TD
    subgraph Orchestrator_Call [Orchestrator Call]
        Start([User Input from Orchestrator]) --> A[RiskManagingAgent.run]
    end

    subgraph RiskManagingAgent_Internal [RiskManagingAgent Internal Workflow]
        A --> B{Is triggered or similar? <br/>OR Analysis in progress?}
        B -- No --> C[Passthrough to Default]
        B -- Yes --> D[Set analysis_in_progress = True]

        D --> E[ConversationManager.assess_conversation_progress]
        E --> F{analysis_ready? <br/>Enough info collected?}
        
        F -- No --> G[Generate Follow-up Questions]
        G --> H[Return follow-up response]
        
        F -- Yes --> I[RAGConnector.get_risk_documents]
        I --> J[backend.rag.retriever.search]
        J --> K[Filter RAG docs by RAG_DATASETS]
        K --> L[Extract Similar Cases & Evidence]
        L --> M[RiskEngine.evaluate_risk]
        M --> N[ReportGenerator.generate_report]
        N --> O[Return JSON RiskReport <br/>Set analysis_in_progress = False]
    end

    C --> End([To Orchestrator/Default Agent])
    H --> End
    O --> End

    %% 스타일 설정
    style A fill:#f9f,stroke:#333,stroke-width:2px
    style B fill:#add8e6,stroke:#333,stroke-width:2px
    style C fill:#ffe4e1,stroke:#333,stroke-width:2px
    style D fill:#90ee90,stroke:#333,stroke-width:2px
    style E fill:#add8e6,stroke:#333,stroke-width:2px
    style F fill:#add8e6,stroke:#333,stroke-width:2px
    style G fill:#f0e68c,stroke:#333,stroke-width:2px
    style H fill:#90ee90,stroke:#333,stroke-width:2px
    style I fill:#add8e6,stroke:#333,stroke-width:2px
    style J fill:#add8e6,stroke:#333,stroke-width:2px
    style K fill:#add8e6,stroke:#333,stroke-width:2px
    style L fill:#add8e6,stroke:#333,stroke-width:2px
    style M fill:#add8e6,stroke:#333,stroke-width:2px
    style N fill:#add8e6,stroke:#333,stroke-width:2px
    style O fill:#f0e68c,stroke:#333,stroke-width:2px