"""
CEO Simulator Agent - Simulate CEO persona for report practice
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


class CEOAgent:
    """Simulate CEO persona for report practice"""
    
    def __init__(self):
        self.llm = ChatUpstage(
            model="solar-pro-preview-240910",
            api_key=os.getenv("UPSTAGE_API_KEY")
        )
        self.retriever = FAISSRetriever()
        self.context_builder = ContextBuilder()
    
    @traceable(name="ceo_agent_run")
    def run(self, user_input: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Simulate CEO interaction
        
        Args:
            user_input: User's report or question
            context: Optional context
        
        Returns:
            CEO response
        """
        # Retrieve CEO style and decision-making patterns
        ceo_docs = self.retriever.retrieve(
            query=user_input,
            category="ceo_style",
            top_k=5
        )
        
        # Get KPI data for context
        kpi_docs = self.retriever.retrieve(
            query="performance metrics",
            category="kpi",
            top_k=2
        )
        
        all_docs = ceo_docs + kpi_docs
        
        # Build context
        context_text = self.context_builder.build_context(
            query=user_input,
            retrieved_docs=all_docs,
            agent_type="ceo"
        )
        
        # Generate CEO response
        system_prompt = self.context_builder._get_system_prompt("ceo")
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"""신입사원의 보고를 듣고 대표로서 질문하고 피드백해주세요.

## 대표 스타일 참고
{context_text}

## 신입사원 보고
{user_input}

## 응답 형식
대표로서 자연스럽게 응답하되, 다음을 포함:
1. 보고 내용에 대한 핵심 질문 (2-3개)
2. 추가로 필요한 정보
3. 의사결정을 위한 리스크 확인
4. 간단한 피드백

톤: 직접적이고 간결하게, 하지만 신입사원을 배려하는 톤
""")
        ]
        
        try:
            response = self.llm.invoke(messages)
            
            return {
                "response": response.content,
                "metadata": {
                    "retrieved_docs": len(all_docs),
                    "report_length": len(user_input)
                }
            }
        except Exception as e:
            return {
                "response": f"CEO 시뮬레이션 중 오류가 발생했습니다: {str(e)}",
                "metadata": {"error": str(e)}
            }


def main():
    """Test CEO agent"""
    print("=" * 60)
    print("CEO Agent Test")
    print("=" * 60)
    
    agent = CEOAgent()
    
    # Test report
    report = """
    대표님, 브라질 거래처에서 FOB 조건으로 100톤 주문이 들어왔습니다.
    가격은 톤당 $2,500이고, 다음 주 선적 요청입니다.
    """
    
    result = agent.run(report)
    print("\n" + result["response"])


if __name__ == "__main__":
    main()
