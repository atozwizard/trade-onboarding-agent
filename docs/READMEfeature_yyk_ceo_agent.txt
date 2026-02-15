PR: backend/agents 구조 설계 및 CEO Agent 1차 구현
📌 개요

AI 코칭 플랫폼의 핵심 로직인 agent 기반 응답 구조를 구축하고, 그 중 ceo_agent를 우선적으로 구현했습니다.
본 PR은 향후 email/mistake/quiz 등 다른 에이전트 확장을 위한 표준 구조 확립을 목표로 합니다.

🎯 기획 의도

본 프로젝트는 단순 챗봇이 아닌
무역·물류 도메인 특화 AI 코칭 시스템 구축을 목표로 합니다.

이를 위해:

단일 LLM 응답 구조 ❌

전문화된 agent 기반 구조 ⭕

로 설계되었습니다.

각 agent는 특정 역할을 담당하며
RAG + LLM 기반으로 실제 업무 상황 코칭을 수행합니다.

🧠 전체 아키텍처 방향
User Input
   ↓
(향후 orchestrator 또는 직접 agent 호출)
   ↓
Agent (ceo/email/mistake/quiz)
   ↓
RAG 검색 (Chroma + Solar embedding)
   ↓
Solar Pro2 추론
   ↓
구조화된 응답 반환

🧩 backend/agents 개발사항
1. Agent 표준 인터페이스 구조 정립

모든 agent는 동일한 반환 구조를 따르도록 설계:

{
  "response": str,
  "agent_type": str,
  "metadata": dict
}

목적

FastAPI 연동 단순화

orchestrator 확장 대비

logging / tracing 통일

테스트 용이성 확보

2. 프롬프트 외부 파일 분리 구조

각 agent는:

backend/prompts/*_prompt.txt


를 system prompt로 사용.

이유

프롬프트 수정 시 코드 수정 불필요

기획/운영팀 협업 가능

A/B 테스트 가능

향후 LangSmith prompt 관리 연동 대비

3. RAG 기반 응답 구조 통합

ceo_agent 기준:

embedder → Upstage Solar embedding

retriever → ChromaDB 검색

metadata 포함 문서 반환

LLM 입력에 RAG context 삽입

목적

단순 생성형 응답이 아닌
도메인 기반 의사결정 코칭

4. Upstage Solar Pro2 LLM 연동

ceo_agent는:

solar-pro2


기반으로 응답 생성.

system prompt: ceo_prompt.txt

user_input + context

rag 검색 결과 포함

5. LangSmith tracing 구조 추가

AI 응답 흐름 추적을 위해:

LangSmith tracing 환경변수 설정

agent 단위 trace 가능 구조

향후 전체 agent observability 확보

목적

추론 과정 디버깅

프롬프트 개선

응답 품질 분석

운영 모니터링

🤝 협업 고려 설계

현재 팀 개발 구조:

영역	상태
다른 agent	팀원별 개발 예정
orchestrator	생성 완료, 사용 여부 미정
API 연결	stub 상태
RAG	연결 완료
LLM	Solar 기준 통일

ceo_agent는
다른 agent 개발 시 reference 구현체 역할.

🚀 향후 예정 (후속 PR)

email_agent 구현

mistake_agent 구현

quiz_agent 구현

orchestrator 연결 여부 결정

FastAPI endpoint 통합

streaming 여부 검토

🧾 요약

이번 PR은:

agent 기반 AI 코칭 아키텍처의 첫 실제 구현

이며,

프롬프트 외부화

RAG 통합

Solar 연동

tracing 기반 observability

까지 고려한
확장 가능한 구조 초석 작업입니다.