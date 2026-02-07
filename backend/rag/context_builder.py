"""
Context Builder - Assemble retrieved documents into LLM prompts
"""

from typing import List, Dict, Any


class ContextBuilder:
    """Build context from retrieved documents for LLM prompts"""
    
    @staticmethod
    def build_context(
        query: str,
        retrieved_docs: List[Dict[str, Any]],
        agent_type: str = "general"
    ) -> str:
        """
        Build context string from retrieved documents
        
        Args:
            query: User query
            retrieved_docs: List of retrieved documents
            agent_type: Type of agent (quiz, email, ceo, mistake)
        
        Returns:
            Formatted context string
        """
        if not retrieved_docs:
            return "관련 정보를 찾을 수 없습니다."
        
        # Build context sections
        context_parts = []
        
        # Group by category
        by_category = {}
        for doc in retrieved_docs:
            category = doc["category"]
            if category not in by_category:
                by_category[category] = []
            by_category[category].append(doc)
        
        # Format each category
        for category, docs in by_category.items():
            category_name = ContextBuilder._get_category_name(category)
            context_parts.append(f"## {category_name}")
            
            for i, doc in enumerate(docs, 1):
                context_parts.append(f"{i}. {doc['text']}")
            
            context_parts.append("")  # Empty line
        
        return "\n".join(context_parts)
    
    @staticmethod
    def build_agent_prompt(
        query: str,
        context: str,
        agent_type: str
    ) -> str:
        """
        Build complete prompt for specific agent type
        
        Args:
            query: User query
            context: Retrieved context
            agent_type: Type of agent
        
        Returns:
            Complete prompt string
        """
        # Load agent-specific system prompt
        system_prompt = ContextBuilder._get_system_prompt(agent_type)
        
        # Combine into final prompt
        prompt = f"""{system_prompt}

## 참고 자료
{context}

## 사용자 질문
{query}

## 답변
"""
        return prompt
    
    @staticmethod
    def _get_category_name(category: str) -> str:
        """Get Korean name for category"""
        category_names = {
            "company_domain": "회사 도메인 지식",
            "internal_process": "내부 프로세스",
            "mistakes": "실수 사례",
            "ceo_style": "대표 의사결정 스타일",
            "emails": "이메일 예시",
            "country_rules": "국가별 특징",
            "negotiation": "가격 협상 사례",
            "claims": "클레임 사례",
            "document_errors": "서류 오류 패턴",
            "trade_qa": "무역 용어 Q&A",
            "kpi": "KPI 데이터",
            "quiz_samples": "퀴즈 샘플"
        }
        return category_names.get(category, category)
    
    @staticmethod
    def _get_system_prompt(agent_type: str) -> str:
        """Get system prompt for agent type"""
        prompts = {
            "quiz": """당신은 무역회사 신입사원을 위한 온보딩 퀴즈 생성 전문가입니다.
실무에 필요한 무역 용어와 프로세스에 대한 퀴즈를 생성하고, 정답과 상세한 해설을 제공합니다.
퀴즈는 실전에 도움이 되도록 구체적인 상황을 포함해야 합니다.""",
            
            "email": """당신은 15년차 무역회사 팀장입니다.
신입사원이 작성한 이메일을 검토하고, 톤, 리스크, 정확성을 분석합니다.
실수 가능성을 지적하고 개선된 버전을 제시합니다.
대표의 스타일(리스크 회피형, 간결 선호)을 반영하여 피드백합니다.""",
            
            "ceo": """당신은 중소 커피생두 무역회사의 대표입니다.
특징: 리스크 회피형, 거래 안정성 중시, 실수를 매우 싫어함, 보고는 간결하게 선호
신입사원의 보고를 듣고 핵심적인 질문을 던지며, 의사결정에 필요한 정보를 요구합니다.""",
            
            "mistake": """당신은 무역 실무 리스크 관리 전문가입니다.
주어진 상황에서 신입사원이 저지를 수 있는 실수 3가지를 예측하고,
각 실수에 대한 예방 방법과 체크리스트를 제공합니다.
과거 사례를 참고하여 구체적으로 설명합니다.""",
            
            "general": """당신은 무역회사 신입사원을 돕는 AI 어시스턴트입니다.
무역 용어, 프로세스, 실무 팁에 대해 친절하고 명확하게 설명합니다."""
        }
        
        return prompts.get(agent_type, prompts["general"])
    
    @staticmethod
    def format_quiz_response(quiz_data: Dict[str, Any]) -> str:
        """Format quiz response"""
        return f"""## 퀴즈

**문제**: {quiz_data.get('question', '')}

**선택지**:
{quiz_data.get('choices', '')}

**정답**: {quiz_data.get('answer', '')}

**해설**: {quiz_data.get('explanation', '')}

**실무 팁**: {quiz_data.get('tip', '')}
"""
    
    @staticmethod
    def format_email_feedback(feedback_data: Dict[str, Any]) -> str:
        """Format email coaching feedback"""
        return f"""## 이메일 피드백

### 원본 분석
- **톤**: {feedback_data.get('tone_analysis', '')}
- **리스크**: {feedback_data.get('risk_analysis', '')}
- **개선 필요 사항**: {feedback_data.get('improvements', '')}

### 수정 버전
```
{feedback_data.get('revised_email', '')}
```

### 주요 변경 사항
{feedback_data.get('changes', '')}
"""


def main():
    """Test context builder"""
    # Sample retrieved docs
    sample_docs = [
        {
            "text": "BL (Bill of Lading) - 선하증권 | 선적 후 발행 | 오기재시 수정비용 | 선적·통관",
            "category": "company_domain",
            "score": 0.95
        },
        {
            "text": "consignee 회사명 오타 → BL 재발행",
            "category": "mistakes",
            "score": 0.87
        }
    ]
    
    builder = ContextBuilder()
    
    # Test context building
    context = builder.build_context(
        query="BL이 뭐야?",
        retrieved_docs=sample_docs,
        agent_type="general"
    )
    
    print("=" * 60)
    print("Context Builder Test")
    print("=" * 60)
    print(context)
    
    # Test full prompt
    prompt = builder.build_agent_prompt(
        query="BL이 뭐야?",
        context=context,
        agent_type="general"
    )
    
    print("\n" + "=" * 60)
    print("Full Prompt")
    print("=" * 60)
    print(prompt)


if __name__ == "__main__":
    main()
