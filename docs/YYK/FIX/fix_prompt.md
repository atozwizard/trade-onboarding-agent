# [FIX] 리스크 관리 에이전트 유연성 및 분석 로직 고도화

## 1. 개요 (Overview)
기존 리스크 관리 에이전트(RiskManaging)의 정보 수집 로직이 지나치게 경직되어 있어, 사용자가 정보를 제공하지 못하는 상황에서도 반복적으로 질문만 던지는 '정보 루프(Loop)' 문제가 식별되었습니다. 이를 해결하기 위해 **가설 기반 분석(Hypothesis-based Analysis)** 시스템을 도입하고 상태 관리 로직을 개선했습니다.

## 2. 주요 수정 내용 (Key Improvements)

### 2.1 가설 기반 분석 시스템 도입
*   **정보 루프 탈출**: 사용자가 정보를 모른다고 하거나 즉시 분석을 원할 경우(예: "모른다", "그냥 해줘"), 시스템이 이를 감지하고 자동으로 분석 단계(`sufficient`)로 넘어가도록 수정했습니다.
*   **통계적 추정 및 관례 적용**: 특정 데이터(계약 금액, 페널티 조항 등)가 없을 때, "정보 없음"으로 보류하는 대신 **일반적인 무역 관습, 인코텀즈 규정, 유사 비즈니스 케이스**를 바탕으로 가설을 설정하여 리스크를 평가합니다.

### 2.2 프롬프트 고도화 (Prompt Engineering)
*   **`CONVERSATION_ASSESSMENT_PROMPT`**: 정보 수집 단계에서 '유연한 판단' 지침을 추가했습니다.
*   **`RISK_ENGINE_EVALUATION_PROMPT`**: "통상적인 경우 ~하므로 ~한 리스크가 예상된다"는 식의 가설적 조언을 생성하도록 명시적 가이드라인을 주입했습니다.
*   **`riskmanaging_prompt.txt`**: 시스템 프롬프트 수준에서 **Actionable Advice** 우선 원칙과 가설 수립 기준을 확립했습니다.

### 2.3 상태 관리 및 중복 질문 방지 (State Management)
*   **데이터 병합 로직 (Merge Extracted Data)**: 대화가 진행됨에 따라 새롭게 추출된 정보를 기존 정보와 병합하도록 하여, 이미 언급된 정보(예: "7억")를 다시 묻는 UX 결함을 해결했습니다.
*   **컨텍스트 주입**: 파악된 모든 사실 관계(`extracted_data`)를 매 단계 프롬프트에 포함시켜 LLM이 문맥을 완벽히 이해하도록 개선했습니다.

## 3. 세부 변경 파일
*   **`backend/agents/riskmanaging/nodes.py`**:
    *   프롬프트 내 `{{extracted_data}}` 치환 로직 추가.
    *   `assess_conversation_progress_node` 내 데이터 병합 로직 구현.
*   **`backend/prompts/riskmanaging_prompt.txt`**:
    *   유연한 분석 및 가설 기반 지침(Flexible Analysis & Hypothesis Guidelines) 추가.
*   **`scripts/verify_integration.py`**:
    *   가설 기반 분석을 테스트하는 `test_hypothesis_analysis` 케이스 추가 및 검증 완료.

## 4. 기대 효과
*   **UX 향상**: 사용자가 막히는 부분에서 AI가 선제적으로 가설을 제시함으로써 대화의 단절을 막고 실무적인 통찰을 제공합니다.
*   **신뢰도 확보**: 정보가 부족한 상황임을 인지시키면서도 전문가 수준의 추정치를 제공하여 AI의 전문성을 강조합니다.
*   **성능 최적화**: 중복 질문을 제거하여 대화 턴 수를 줄이고 핵심 결론에 도달하는 시간을 단축합니다.
