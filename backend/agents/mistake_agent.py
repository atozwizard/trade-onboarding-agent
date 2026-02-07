"""
Mistake Predictor Agent - Predict potential mistakes in given situations
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


class MistakeAgent:
    """Predict potential mistakes and provide prevention strategies"""
    
    def __init__(self):
        self.llm = ChatUpstage(
            model="solar-pro-preview-240910",
            api_key=os.getenv("UPSTAGE_API_KEY")
        )
        self.retriever = FAISSRetriever()
        self.context_builder = ContextBuilder()
    
    @traceable(name="mistake_agent_run")
    def run(self, user_input: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Predict mistakes for a given situation
        
        Args:
            user_input: Situation description
            context: Optional context
        
        Returns:
            Mistake predictions and prevention strategies
        """
        # Retrieve relevant mistake cases
        mistake_docs = self.retriever.retrieve(
            query=user_input,
            category="mistakes",
            top_k=5
        )
        
        # Also get document errors
        doc_error_docs = self.retriever.retrieve(
            query=user_input,
            category="document_errors",
            top_k=3
        )
        
        all_docs = mistake_docs + doc_error_docs
        
        # Build context
        context_text = self.context_builder.build_context(
            query=user_input,
            retrieved_docs=all_docs,
            agent_type="mistake"
        )
        
        # Generate predictions
        system_prompt = self.context_builder._get_system_prompt("mistake")
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"""다음 상황에서 신입사원이 저지를 수 있는 실수를 예측해주세요.

## 참고 자료 (과거 실수 사례)
{context_text}

## 상황
{user_input}

## 예측 형식
**예상 실수 1**: [실수 내용]
- **원인**: [왜 이런 실수가 발생하는지]
- **결과**: [이 실수의 영향]
- **예방 방법**: [구체적인 예방 조치]

**예상 실수 2**: [실수 내용]
- **원인**: [왜 이런 실수가 발생하는지]
- **결과**: [이 실수의 영향]
- **예방 방법**: [구체적인 예방 조치]

**예상 실수 3**: [실수 내용]
- **원인**: [왜 이런 실수가 발생하는지]
- **결과**: [이 실수의 영향]
- **예방 방법**: [구체적인 예방 조치]

**체크리스트**:
- [ ] 항목 1
- [ ] 항목 2
- [ ] 항목 3
""")
        ]
        
        try:
            response = self.llm.invoke(messages)
            
            return {
                "response": response.content,
                "metadata": {
                    "retrieved_docs": len(all_docs),
                    "situation": user_input
                }
            }
        except Exception as e:
            return {
                "response": f"실수 예측 중 오류가 발생했습니다: {str(e)}",
                "metadata": {"error": str(e)}
            }


def main():
    """Test mistake agent"""
    print("=" * 60)
    print("Mistake Agent Test")
    print("=" * 60)
    
    agent = MistakeAgent()
    
    # Test situation
    situation = "BL을 처음 작성하는 상황입니다. 어떤 실수를 조심해야 할까요?"
    
    result = agent.run(situation)
    print("\n" + result["response"])


if __name__ == "__main__":
    main()
