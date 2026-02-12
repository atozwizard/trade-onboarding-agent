# backend/agents/riskmanaging/config.py

# Trigger words for Risk Managing Agent automatic execution
RISK_AGENT_TRIGGER_WORDS = [
    "실수",
    "클레임",
    "지연",
    "문제",
    "리스크",
    "invoice",
    "선적",
    "hs code",
    "payment",
    "계약",
    "괜찮을까",
    "확인 부탁",
]

# Cosine similarity threshold for triggering
SIMILARITY_THRESHOLD = 0.87

# Enterprise Risk Engine Evaluation Items
RISK_EVALUATION_ITEMS = {
    "financial_loss": {"name": "재정적 손실", "description": "프로젝트로 인해 발생할 수 있는 직접적/간접적 금전적 손실"},
    "delay": {"name": "일정 지연", "description": "프로젝트 완료 또는 목표 달성 일정 지연 가능성"},
    "relationship_risk": {"name": "관계 리스크", "description": "내부 팀, 외부 파트너, 고객 등 이해관계자와의 관계 손상 가능성"},
    "compliance_risk": {"name": "규제/법률 준수 리스크", "description": "법규, 회사 정책, 국제 규정 등 준수 여부 및 위반 시 발생할 수 있는 리스크"},
    "internal_blame_risk": {"name": "내부 책임/비난 리스크", "description": "프로젝트 실패 시 내부적으로 발생할 수 있는 책임 추궁 및 비난의 강도"},
}

# Risk Level thresholds based on risk_score (Impact * Likelihood)
RISK_LEVEL_THRESHOLDS = {
    "critical": 15,  # e.g., 5(Impact) * 3(Likelihood) = 15 or higher
    "high": 10,      # e.g., 5*2=10, 4*3=12
    "medium": 5,     # e.g., 5*1=5, 2*3=6
    "low": 1,        # e.g., 1*1=1
}

# Datasets for RAG
RAG_DATASETS = [
    "claims",
    "mistakes",
    "emails",
    "country_rules",
]

# Persona configuration for the agent
AGENT_PERSONA = {
    "tone": "담백하고 직설적",
    "emotional_expression": "금지",
    "exaggeration": "금지",
    "feedback_style": "실제 회사 상사 피드백 톤 유지",
    "judgment_criteria": [
        "회사 기준",
        "실무 기준",
        "실제 발생 가능한 리스크",
        "내부 보고 기준",
    ],
    "response_style": "친절한 설명형이 아니라 실무 피드백 형식",
    "always_include": [
        "무엇이 문제인지",
        "왜 문제인지",
        "실제 발생 가능한 상황",
        "지금 해야 할 행동",
    ],
    "never_include": [
        "과도한 공감",
        "감정 위로",
        "불필요한 장문 설명",
        "추상적 조언",
    ],
}
