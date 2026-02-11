---             
  🔄 전체 흐름도                                                                                                        
                                                                                                                        
  [사용자 질문]
        ↓
  [Orchestrator] 의도 분류
        ↓
  [각 Agent] retriever로 관련 지식 검색
        ↓
  [LLM] 검색 결과 + 프롬프트 → 응답 생성
        ↓
  [사용자에게 응답]

  ---
  📚 실제 사용 예시

  1️⃣ Quiz Agent - 퀴즈 생성

  # backend/agents/quiz_agent.py (예시)

  from backend.rag.retriever import search_with_filter

  class QuizAgent:
      def generate_quiz(self, topic: str, difficulty: str):
          """
          주제와 난이도에 맞는 퀴즈 생성
          """
          # 1. retriever로 퀴즈 샘플 + 관련 지식 검색
          quiz_samples = search_with_filter(
              query=f"{topic} 관련 퀴즈",
              k=5,
              document_type="quiz_question",  # 퀴즈 문서만
              topic=topic,                    # 주제 필터
              level=difficulty                # 난이도 필터
          )

          # 도메인 지식도 함께 검색
          domain_knowledge = search_with_filter(
              query=topic,
              k=3,
              document_type="terminology"  # 용어 설명
          )

          # 2. 검색 결과를 컨텍스트로 만들기
          context = {
              "quiz_samples": [doc["document"] for doc in quiz_samples],
              "knowledge": [doc["document"] for doc in domain_knowledge]
          }

          # 3. LLM에게 전달
          prompt = f"""
          다음 참고 자료를 바탕으로 {topic} 퀴즈를 생성하세요.
   
          [참고 퀴즈 샘플]
          {context['quiz_samples']}
   
          [도메인 지식]
          {context['knowledge']}
   
          난이도: {difficulty}
          """

          # LLM 호출 (할루시네이션 방지!)
          response = self.llm.invoke(prompt)
          return response

  왜 이렇게 사용하나요?
  - ✅ 할루시네이션 방지: 실제 퀴즈 샘플을 참고해서 생성
  - ✅ 난이도 조절: level 필터로 적절한 난이도 샘플만 가져옴
  - ✅ 정확한 용어: 도메인 지식을 함께 검색해서 정확한 용어 사용

  ---
  2️⃣ Email Coach Agent - 이메일 검토

  # backend/agents/email_agent.py (예시)

  from backend.rag.retriever import search_with_filter

  class EmailCoachAgent:
      def review_email(self, user_email: str, situation: str):
          """
          사용자가 작성한 이메일을 검토하고 피드백 제공
          """
          # 1. 유사한 상황의 이메일 템플릿 검색
          similar_emails = search_with_filter(
              query=user_email,
              k=3,
              document_type="email",      # 이메일 문서만
              situation=situation         # 상황별 필터링
          )

          # 2. 실수 사례 검색 (리스크 탐지용)
          common_mistakes = search_with_filter(
              query=f"이메일 작성 시 주의사항 {situation}",
              k=3,
              document_type="common_mistake",  # 실수 사례
              priority="critical"               # 긴급 실수만
          )

          # 3. 컨텍스트 구성
          context = {
              "good_examples": similar_emails,
              "mistakes_to_avoid": common_mistakes
          }

          prompt = f"""
          사용자 이메일:
          {user_email}
   
          [참고할 좋은 예시]
          {context['good_examples']}
   
          [피해야 할 실수]
          {context['mistakes_to_avoid']}
   
          위 자료를 바탕으로:
          1. 리스크 탐지 (실수 사례와 비교)
          2. 톤 보정 제안
          3. 수정안 제공
          """

          return self.llm.invoke(prompt)

  실제 사용 시나리오:
  사용자: "고객에게 선적 지연 사과 이메일 보내려고 하는데 검토해줘"

  → retriever 검색:
    - "선적 지연 사과" 관련 이메일 3개 (좋은 예시)
    - "이메일 실수" 중 critical 우선순위 3개 (피해야 할 실수)

  → LLM 응답:
    "⚠️  리스크: '곧 보내드리겠습니다'는 모호한 표현입니다.
     ✅ 수정안: '3월 15일까지 배송 예정입니다'처럼 명확한 날짜를 제시하세요."

  ---
  3️⃣ Mistake Predictor Agent - 실수 예측

  # backend/agents/mistake_agent.py (예시)

  from backend.rag.retriever import search_with_filter

  class MistakePredictorAgent:
      def predict_mistakes(self, task: str, user_role: str):
          """
          업무 상황별 예상 실수 TOP 3 제공
          """
          # 1. 해당 업무의 실수 사례 검색
          mistakes = search_with_filter(
              query=f"{task} 업무 시 실수",
              k=10,
              document_type="common_mistake",  # 실수 사례만
              role=user_role,                  # 역할별 필터링
              priority=None                    # 모든 우선순위
          )

          # 2. 우선순위 순으로 정렬 (critical > high > normal)
          priority_order = {"critical": 1, "high": 2, "normal": 3}
          sorted_mistakes = sorted(
              mistakes,
              key=lambda x: priority_order.get(x["metadata"]["priority"], 999)
          )

          # 3. TOP 3 선정
          top3_mistakes = sorted_mistakes[:3]

          # 4. 예방 체크리스트 생성
          prompt = f"""
          {task} 업무의 주요 실수 사례:
   
          {[m["document"] for m in top3_mistakes]}
   
          위 실수를 예방하기 위한 체크리스트를 작성하세요.
          """

          checklist = self.llm.invoke(prompt)

          return {
              "top3_mistakes": top3_mistakes,
              "checklist": checklist
          }

  실제 사용 시나리오:
  사용자: "BL 작성할 건데 주의할 점 알려줘"

  → retriever 검색:
    1. "BL 오기재 | 검토누락 | 통관지연" (priority: critical)
    2. "incoterms 잘못 사용" (priority: critical)
    3. "HS Code 오류" (priority: high)

  → 응답:
    "⚠️  TOP 3 예상 실수:
     1. BL 오기재 → 더블체크 필수
     2. Incoterms 확인 → 계약서와 일치 여부 확인
     3. HS Code 검증 → 관세청 사이트에서 재확인

     ✅ 체크리스트:
     □ BL 내용과 계약서 대조
     □ Incoterms 일치 여부 확인
     □ HS Code 관세청 DB 대조"

  ---
  4️⃣ CEO Simulator Agent - 대표 보고 연습

  # backend/agents/ceo_agent.py (예시)

  from backend.rag.retriever import search_with_filter

  class CEOSimulatorAgent:
      def simulate_ceo_response(self, user_report: str, situation: str):
          """
          CEO에게 보고하는 시뮬레이션
          """
          # 1. CEO 스타일 검색
          ceo_style = search_with_filter(
              query=f"{situation} 상황 CEO 반응",
              k=3,
              document_type="ceo_guideline",  # CEO 가이드라인만
              level="executive",
              situation=situation
          )

          # 2. 협상 사례 검색 (참고용)
          negotiation_cases = search_with_filter(
              query=situation,
              k=2,
              document_type="negotiation_strategy"
          )

          prompt = f"""
          당신은 15년차 무역 회사 대표입니다.
   
          [당신의 의사결정 스타일]
          {ceo_style}
   
          [참고 사례]
          {negotiation_cases}
   
          직원 보고:
          {user_report}
   
          위 스타일에 맞춰 질문하고 피드백하세요.
          """

          return self.llm.invoke(prompt)

  실제 사용 시나리오:
  사용자: "대표님, 선적이 3일 지연될 것 같습니다."

  → retriever 검색:
    - CEO 스타일: "긴급결정 | 리스크 | 팀장공유"
    - CEO 초점: "거래처신뢰" (critical)

  → CEO 시뮬레이터 응답:
    "3일이라는 게 확정인가, 최악의 경우인가?
     고객한테는 언제 연락했나?
     대안은 있나? (Air로 일부라도 먼저 보낼 수 있나?)
     → 이런 식으로 구체적 정보와 대안을 먼저 준비해야 해."

  ---
  🎯 핵심 패턴 정리

  📌 모든 에이전트의 공통 패턴

  # 1. 관련 지식 검색 (retriever 사용)
  context = search_with_filter(
      query=user_input,
      k=3-5,
      document_type="...",  # 에이전트별로 다름
      situation="...",
      priority="..."
  )

  # 2. 컨텍스트를 프롬프트에 삽입
  prompt = f"""
  {base_prompt}

  [참고 자료]
  {context}

  [사용자 입력]
  {user_input}
  """

  # 3. LLM 호출
  response = llm.invoke(prompt)

  ---
  🔍 각 에이전트별 retriever 사용법
  ┌───────────────────┬─────────────────────────────────────┬──────────────────────────────┐
  │     에이전트      │     주로 검색하는 document_type     │         필터링 기준          │
  ├───────────────────┼─────────────────────────────────────┼──────────────────────────────┤
  │ Quiz Agent        │ quiz_question, terminology          │ topic, level                 │
  ├───────────────────┼─────────────────────────────────────┼──────────────────────────────┤
  │ Email Coach       │ email, common_mistake               │ situation, priority          │
  ├───────────────────┼─────────────────────────────────────┼──────────────────────────────┤
  │ Mistake Predictor │ common_mistake, error_checklist     │ role, priority               │
  ├───────────────────┼─────────────────────────────────────┼──────────────────────────────┤
  │ CEO Simulator     │ ceo_guideline, negotiation_strategy │ level="executive", situation │
  └───────────────────┴─────────────────────────────────────┴──────────────────────────────┘
  ---
  💡 왜 이렇게 나눠서 검색하나요?

  ❌ 나쁜 예 (모든 데이터 한번에 검색)

  # 비효율적: 200개 문서 전체에서 검색
  all_docs = search("BL 작성", k=10)
  # → 퀴즈, 이메일, KPI 등 관련 없는 문서도 섞여 나옴

  ✅ 좋은 예 (필터로 정확한 문서만)

  # 효율적: 실수 사례만 검색
  mistakes_only = search_with_filter(
      query="BL 작성",
      k=5,
      document_type="common_mistake",  # 실수 사례만!
      priority="critical"               # 긴급한 것만!
  )
  # → 정확히 필요한 5개 문서만 가져옴

  장점:
  - ⚡ 속도: 필터링으로 검색 범위 축소
  - 🎯 정확도: 불필요한 노이즈 제거
  - 💰 비용: LLM에 전달하는 토큰 수 감소

  ---
  📊 실전 예시: Email Coach의 전체 흐름

  # 사용자 입력
  user_email = "고객님께, 선적이 조금 늦어질 것 같습니다. 양해 부탁드립니다."
  situation = "delay_apology"

  # STEP 1: 좋은 예시 검색
  good_examples = search_with_filter(
      query="선적 지연 사과 이메일",
      k=2,
      document_type="email",
      situation="delay"
  )
  # 결과: ["저희 선적이 3일 지연되어...", "배송이 지연되어 진심으로..."]

  # STEP 2: 실수 사례 검색
  mistakes = search_with_filter(
      query="이메일 작성 실수",
      k=3,
      document_type="common_mistake",
      priority="critical"
  )
  # 결과: ["모호한 표현 사용", "책임 회피 표현", "구체적 날짜 미제시"]

  # STEP 3: LLM에 전달
  prompt = f"""
  [사용자 이메일]
  {user_email}

  [좋은 예시]
  {good_examples}

  [피해야 할 실수]
  {mistakes}

  위 자료를 바탕으로 피드백하세요.
  """

  # STEP 4: LLM 응답
  """
  ⚠️  리스크 발견:
  1. "조금"은 모호한 표현 → 구체적 날짜 필요
  2. "양해 부탁" → 책임 회피 느낌

  ✅ 수정안:
  "고객님께, 선적이 3월 15일로 3일 지연될 예정입니다.
  저희 측 일정 관리 미흡으로 불편을 드려 죄송합니다.
  현재 Air 배송 대안을 검토 중이며, 오늘 중 재연락드리겠습니다."
  """

  ---
  🎓 정리

  Retriever의 역할

  1. 할루시네이션 방지: LLM이 지어내지 않도록 실제 데이터 제공
  2. 도메인 정확성: 무역 용어, 프로세스 정확히 전달
  3. 컨텍스트 제공: 예시, 사례, 가이드라인 제공

  Schema의 역할

  - 필터링을 가능하게 만드는 메타데이터 통일

  Embedder의 역할

  - 의미 기반 검색을 가능하게 하는 벡터 변환

  삼총사가 함께 일하면 = 정확하고 빠른 AI 코치 완성! 🎉

