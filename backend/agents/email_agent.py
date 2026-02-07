"""
Email Coach Agent - Provide feedback on email drafts
"""

import os
import sys
from typing import Dict, Any, Optional
from dotenv import load_dotenv
from langchain_upstage import ChatUpstage
from langchain.schema import HumanMessage, SystemMessage
from langsmith import traceable

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from rag.retriever import FAISSRetriever
from rag.context_builder import ContextBuilder

load_dotenv()


class EmailAgent:
    """Coach users on email writing"""
    
    def __init__(self):
        self.llm = ChatUpstage(
            model="solar-pro-preview-240910",
            api_key=os.getenv("UPSTAGE_API_KEY")
        )
        self.retriever = FAISSRetriever()
        self.context_builder = ContextBuilder()
    
    @traceable(name="email_agent_run")
    def run(self, user_input: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Provide email coaching
        
        Args:
            user_input: User's email draft or request
            context: Optional context
        
        Returns:
            Email feedback
        """
        # Retrieve relevant email examples and mistakes
        email_docs = self.retriever.retrieve(
            query=user_input,
            category="emails",
            top_k=3
        )
        
        mistake_docs = self.retriever.retrieve(
            query=user_input,
            category="mistakes",
            top_k=2
        )
        
        ceo_style_docs = self.retriever.retrieve(
            query="email communication",
            category="ceo_style",
            top_k=2
        )
        
        all_docs = email_docs + mistake_docs + ceo_style_docs
        
        # Build context
        context_text = self.context_builder.build_context(
            query=user_input,
            retrieved_docs=all_docs,
            agent_type="email"
        )
        
        # Generate feedback
        system_prompt = self.context_builder._get_system_prompt("email")
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"""다음 이메일 초안을 검토하고 피드백을 제공해주세요.

## 참고 자료
{context_text}

## 이메일 초안
{user_input}

## 피드백 형식
1. **톤 분석**: 이메일의 톤이 적절한지 평가
2. **리스크 분석**: 잠재적인 문제점이나 오해의 소지
3. **개선 사항**: 구체적인 수정 제안
4. **수정 버전**: 개선된 이메일 전문
5. **주요 변경 사항**: 무엇을 왜 바꿨는지 설명
""")
        ]
        
        try:
            response = self.llm.invoke(messages)
            
            return {
                "response": response.content,
                "metadata": {
                    "retrieved_docs": len(all_docs),
                    "email_length": len(user_input)
                }
            }
        except Exception as e:
            return {
                "response": f"이메일 코칭 중 오류가 발생했습니다: {str(e)}",
                "metadata": {"error": str(e)}
            }


def main():
    """Test email agent"""
    print("=" * 60)
    print("Email Agent Test")
    print("=" * 60)
    
    agent = EmailAgent()
    
    # Test email
    test_email = """
    Dear buyer,
    
    The shipment will be delayed by 3 days.
    
    Best regards
    """
    
    result = agent.run(test_email)
    print("\n" + result["response"])


if __name__ == "__main__":
    main()
