# riskmanaging_agent 감사 보고서

## 1. 사용자 관점 설계 의도

`riskmanaging_agent`는 무역 및 물류 분야 신입사원이 실제 업무 중 발생할 수 있는 잠재적 리스크 상황에 대해 심층적인 분석과 즉각적인 대응 전략을 학습할 수 있도록 돕는 것을 목표로 설계되었습니다. 기존의 `mistake_agent`와 `ceo_agent`의 기능을 병합하여, 단순한 실수 예측을 넘어 실제 의사결정 시뮬레이션까지 아우르는 복합적인 리스크 관리 코칭을 제공합니다.

**핵심 목표:**
-   **리스크 상황 인지**: 사용자가 제시한 상황에서 내재된 리스크 요소를 정확히 식별합니다.
-   **다중 턴 정보 수집**: 불충분한 정보에 대해 사용자에게 구체적인 질문을 하여 완전한 분석을 위한 데이터를 확보합니다.
-   **RAG 기반 심층 분석**: 회사의 내부 지침, 과거 사례, 규정 등 RAG를 통해 검색된 실제 데이터를 기반으로 분석의 정확성을 높입니다.
-   **실전적 보고서 제공**: 단순히 답변을 제공하는 것을 넘어, 구체적인 리스크 평가, 손실 시뮬레이션, 통제 미흡점 분석, 예방 전략 등을 포함하는 구조화된 보고서를 생성합니다.
-   **의사결정 지원**: 보고서를 통해 사용자가 리스크에 대한 종합적인 이해를 바탕으로 합리적인 의사결정을 내릴 수 있도록 돕습니다.

## 2. User Scenario

사용자가 `riskmanaging_agent`와 대화할 때 경험하는 실제 사용 흐름입니다. 다중 턴 대화가 포함됩니다.

**시나리오:** 해외 공급업체의 선적 지연으로 인한 클레임 발생 위험

**사용자:** "해외 공급업체로부터 선적이 지연될 것 같다고 통보받았습니다. 어떻게 해야 할까요?"

**AI 코치 (`riskmanaging_agent`):** "어떤 계약 건인지, 페널티 조항은 있는지, 그리고 지연으로 인해 예상되는 구체적인 영향이 무엇인지 알려주십시오."
*(내부적으로 `conversation_manager`가 `analysis_ready = False`로 판단하고, 추가 정보를 요청)*

**사용자:** "A사와의 10만 달러 규모 계약이고, 5일 이상 지연 시 일당 1%의 페널티가 있습니다. 저희 생산 라인도 멈출 수 있습니다."

**AI 코치 (`riskmanaging_agent`):**
*(내부적으로 `conversation_manager`가 `analysis_ready = True`로 판단하고, `rag_connector`, `risk_engine`, `report_generator`를 순차적으로 호출하여 보고서 생성)*

```json
{
  "analysis_id": "...",
  "input_summary": "사용자가 해외 공급업체의 선적 지연 통보를 받았으며, 이는 A사와의 10만 달러 규모 계약에 해당. 5일 이상 지연 시 일당 1% 페널티가 발생하며, 생산 라인 중단 가능성이 있음.",
  "risk_factors": {
    "재정적 손실": {
      "name_kr": "재정적 손실",
      "impact": 4,
      "likelihood": 4,
      "score": 16,
      "risk_level": "critical"
    },
    "일정 지연": {
      "name_kr": "일정 지연",
      "impact": 5,
      "likelihood": 4,
      "score": 20,
      "risk_level": "critical"
    },
    "생산 차질": {
      "name_kr": "생산 차질",
      "impact": 5,
      "likelihood": 4,
      "score": 20,
      "risk_level": "critical"
    }
  },
  "risk_scoring": {
    "overall_risk_level": "critical",
    "risk_factors": [...],
    "overall_assessment": "해외 공급업체 선적 지연으로 인해 재정적 손실, 생산 일정 지연, 생산 차질 등 심각한 복합적 리스크가 예상됩니다."
  },
  "loss_simulation": {
    "quantitative": null,
    "qualitative": "선적 지연이 5일을 초과할 경우, 계약 금액의 5%인 5,000달러(약 670만원)의 직접적인 페널티 비용이 발생합니다. 또한, 생산 라인 중단은 제조 및 판매 일정에 직접적인 차질을 발생시켜 기회비용 손실 및 고객사와의 신뢰도 하락으로 이어질 수 있습니다."
  },
  "control_gap_analysis": {
    "current_controls": "공급업체와의 계약서상 페널티 조항 존재",
    "identified_gaps": "지연 발생 시 즉각적인 대체 공급망 또는 운송 수단 확보 계획 미비, 공급업체 리스크 평가 및 모니터링 부족",
    "recommendations": "긴급 대체 운송(항공 운송 등) 검토, 공급업체와의 지연 보상 협상 진행, 리스크 발생 시 비상 대응 매뉴얼 수립"
  },
  "prevention_strategy": {
    "short_term": "공급업체와 긴급 협상을 통해 지연 사유 및 확정 납기 확인. 대체 운송 수단 (예: 항공 운송) 긴급 검토 및 비용 산정. 내부 생산 일정 조정 및 관련 부서 공지.",
    "long_term": "복수의 공급업체 확보 및 분산 정책 시행. 계약 시 지연에 대한 강력한 페널티 조항 명시 및 선급금 조건 강화. 공급망 리스크 관리 시스템 구축 및 정기적인 공급업체 평가."
  },
  "similar_cases": [
    {
      "content": "2023년 B사 선적 지연 사례: 생산 라인 5일 중단, 5만 달러 손실 발생",
      "source": "claims.json",
      "topic": ["delay", "claim"]
    },
    {
      "content": "해외 계약 지연 페널티 적용 가이드라인",
      "source": "country_rules.json",
      "topic": ["penalty", "contract"]
    }
  ],
  "confidence_score": 0.85,
  "evidence_sources": ["claims.json", "country_rules.json"]
}
```

## 3. 내부 워크플로 설명 (코드 기준)

`riskmanaging_agent`의 상세 워크플로는 `docs/riskmanaging_workflow.md`에 설명되어 있습니다. 간략히 요약하면 다음과 같습니다.

`riskmanaging_agent.run()` 메서드가 호출되면, 먼저 `trigger_detector`와 `similarity_engine`으로 사용자 입력이 리스크 관리 관련인지 판단합니다. 리스크 관련성이 높거나 진행 중인 분석이 있다면 `analysis_in_progress` 상태로 진입합니다.

이후 `conversation_manager`가 다중 턴 대화를 통해 리스크 분석에 필요한 정보를 충분히 수집했는지(`analysis_ready`) 확인합니다. 정보가 부족하면 추가 질문을 반환하고 대화를 이어갑니다.

`analysis_ready` 상태가 되면 `rag_connector`를 통해 `retriever.search()`로 벡터 DB에서 관련 문서를 검색하고, `riskmanaging` 도메인에 특화된 데이터셋으로 필터링합니다. 검색된 문서와 사용자 입력을 바탕으로 `risk_engine`이 리스크를 평가합니다.

마지막으로 `report_generator`가 LLM을 활용하여 각 섹션의 내용을 채워 상세한 `RiskReport` 객체를 생성하고, 이 객체를 JSON 문자열로 직렬화하여 최종 응답으로 반환합니다. 보고서 반환 후에는 `analysis_in_progress` 플래그를 `False`로 변경하여 리스크 분석 세션을 종료합니다.

## 4. 참조 문서/데이터

`riskmanaging_agent`는 다음의 주요 참조 문서 및 데이터를 활용합니다:

-   **RAG 데이터셋**:
    -   `dataset/*.json` 파일들을 `ChromaDB`에 임베딩하여 구축된 지식 베이스.
    -   특히 `claims.json`, `mistakes.json`, `document_errors.json`, `country_rules.json` 등 리스크 관리에 특화된 데이터셋을 `rag_connector`에서 필터링하여 사용합니다.
-   **LLM (Upstage Solar)**:
    -   `conversation_manager` (정보 부족 시 추가 질문 생성)
    -   `risk_engine` (리스크 평가 및 추론)
    -   `report_generator` (보고서 요약, 손실 시뮬레이션, 통제 미흡점, 예방 전략, 신뢰도 점수 생성)
    -   등의 핵심 로직에서 복잡한 자연어 처리 및 콘텐츠 생성을 위해 활용됩니다.
-   **사전 정의된 프롬프트**: `backend/agents/riskmanaging/prompt_loader.py`에 정의된 프롬프트 템플릿(예: `REPORT_GENERATION_PROMPT`, `INPUT_SUMMARY_PROMPT` 등)을 사용하여 LLM의 동작을 명확히 가이드합니다.

## 5. 문제점 분석 (문서 설계 vs 실제 코드 불일치)

시스템 설계 문서(특히 `AI Workflow Design 기획서_완성본.md`, `Agentic Workflow coLAB template_완성본.md`)와 현재 코드(`orchestrator.py`) 간에 몇 가지 중요한 불일치가 발견되었습니다.

-   **멀티 에이전트 활성화 부족**:
    -   **설계 문서**: `Quiz Agent`, `Email Coach Agent`, `Mistake Predictor Agent`, `CEO Simulator Agent` 4가지 주요 Agent가 Orchestrator에 의해 라우팅되는 멀티 에이전트 시스템으로 설계되었습니다.
    -   **현재 코드**: `backend/agents/orchestrator.py`의 `AGENT_CLASS_MAPPING`에서 `RiskManagingAgent`와 `DefaultChatAgent`를 제외한 모든 Agent 클래스(`QuizAgent`, `EmailAgent`, `MistakeAgent`, `CEOAgent`)가 주석 처리되어 있습니다. 따라서 현재 시스템은 `RiskManagingAgent`만 실질적으로 동작하는 단일 에이전트(혹은 메인 에이전트) 시스템입니다.

-   **Orchestrator의 의도 분류 로직 간소화**:
    -   **설계 문서**: `classify_intent` 노드에서 6가지 카테고리로 명확히 분류하고 `extract_parameters`를 통해 structured output으로 파라미터를 추출하는 복잡한 라우팅 로직이 제시되었습니다.
    -   **현재 코드**: `orchestrator.py`의 `_detect_intent_and_route` 함수는 주로 `active_agent` 우선, `frontend context` 오버라이드, `ORCHESTRATOR_AGENT_TRIGGER_MAP` (현재 `riskmanaging`에 대한 키워드만), `SimilarityEngine` (현재 `riskmanaging`에 대한 유사성만) 기반으로 동작합니다. 설계 문서의 일반적인 의도 분류 및 파라미터 추출 노드와는 차이가 있습니다.

-   **일반적인 RAG 패턴 활용 부족**:
    -   **설계 문서**: `retriever_guide.md` 및 `AI Workflow Design 기획서_완성본.md`에서는 `search_with_filter`를 사용하여 Agent별로 특정 `document_type` 및 메타데이터 필터링을 통해 정교한 RAG 검색을 수행하는 패턴을 제안했습니다.
    -   **현재 코드**: `riskmanaging_agent`는 `rag_connector`를 통해 `backend.rag.retriever.search` 함수만을 호출하며, `search_with_filter`는 사용하지 않습니다. 필터링 로직은 `rag_connector` 내부에서 `RAG_DATASETS` 목록을 기반으로 수동으로 구현되어 있습니다. 이는 설계된 `search_with_filter`의 유연한 활용과는 다릅니다.

## 6. 개선 필요 항목 (리팩토링 전 체크리스트)

위 문제점 분석을 바탕으로, 리팩토링 및 시스템 개선을 위한 체크리스트는 다음과 같습니다.

-   [ ] **Orchestrator의 멀티 에이전트 활성화**: `orchestrator.py`에서 주석 처리된 `QuizAgent`, `EmailAgent`, `MistakeAgent`, `CEOAgent`를 활성화하고, `AGENT_CLASS_MAPPING` 및 `ORCHESTRATOR_AGENT_TRIGGER_MAP`에 추가 설정이 필요합니다.
-   [ ] **Orchestrator의 의도 분류 및 파라미터 추출 로직 강화**: 설계 문서에 명시된 `classify_intent` 및 `extract_parameters` 노드의 역할을 Orchestrator에 구현하거나, 해당 기능을 수행할 별도의 모듈을 통합하여 범용적인 의도 분류 및 파라미터 추출 메커니즘을 구축해야 합니다. 현재 `riskmanaging`에 국한된 로직을 모든 Agent에 적용 가능하도록 일반화해야 합니다.
-   [ ] **모든 Agent에서 `retriever.search_with_filter` 활용**: `rag_connector`의 수동 필터링 대신 `backend.rag.retriever.search_with_filter`의 메타데이터 필터링 기능을 적극적으로 활용하도록 `rag_connector` 및 기타 Agent의 RAG 로직을 수정합니다. 이는 RAG 로직의 일관성과 재사용성을 높일 것입니다.
-   [ ] **`QuizAgent`, `EmailAgent`, `MistakeAgent`, `CEOAgent` 구현 확인**: 이 Agent들이 주석 해제되었을 때 정상적으로 작동할 수 있도록 내부 로직(RAG 활용, LLM 프롬프트, 응답 스키마 등)이 설계 문서에 따라 구현되었는지 확인 및 보강해야 합니다.
-   [ ] **보고서 출력 UI 개선**: 현재 `riskmanaging_agent`는 JSON 문자열로 보고서를 반환하므로, Streamlit 프론트엔드(`frontend/app.py`)에서 이 JSON을 파싱하여 사용자 친화적인 보고서 UI로 렌더링하는 기능이 필요합니다. (STEP 3에서 언급된 "보고서출력" 버튼과 연계될 가능성)
-   [ ] **세션 관리 개선**: 현재 `InMemoryConversationStore`는 개발/데모용으로, 실제 서비스 환경에서는 Redis, 데이터베이스 등으로 교체하여 세션 영속성과 확장성을 확보해야 합니다. (이것은 STEP 4에서 구조 유지를 하면서 수행할 수도 있음)
