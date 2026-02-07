"""
Quiz Agent - Generate and evaluate trade terminology quizzes
"""

import os
import sys
import random
from typing import Dict, Any, Optional
from dotenv import load_dotenv
from langchain_upstage import ChatUpstage
from langchain.schema import HumanMessage, SystemMessage
from langsmith import traceable

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from rag.retriever import FAISSRetriever
from rag.context_builder import ContextBuilder

load_dotenv()


class QuizAgent:
    """Generate quizzes and evaluate answers"""
    
    def __init__(self):
        self.llm = ChatUpstage(
            model="solar-pro-preview-240910",
            api_key=os.getenv("UPSTAGE_API_KEY")
        )
        self.retriever = FAISSRetriever()
        self.context_builder = ContextBuilder()
    
    @traceable(name="quiz_agent_run")
    def run(self, user_input: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Generate a quiz or evaluate an answer
        
        Args:
            user_input: User request
            context: Optional context
        
        Returns:
            Quiz response
        """
        # Check if this is an answer submission
        if context and context.get("quiz_mode") == "answering":
            return self._evaluate_answer(user_input, context)
        
        # Otherwise, generate a new quiz
        return self._generate_quiz(user_input)
    
    @traceable(name="generate_quiz")
    def _generate_quiz(self, user_input: str) -> Dict[str, Any]:
        """Generate a new quiz"""
        # Retrieve relevant content
        retrieved_docs = self.retriever.retrieve(
            query=user_input,
            category="company_domain",
            top_k=3
        )
        
        # Also get quiz samples
        quiz_samples = self.retriever.retrieve(
            query="quiz",
            category="quiz_samples",
            top_k=2
        )
        
        retrieved_docs.extend(quiz_samples)
        
        # Build context
        context = self.context_builder.build_context(
            query=user_input,
            retrieved_docs=retrieved_docs,
            agent_type="quiz"
        )
        
        # Generate quiz using LLM
        system_prompt = self.context_builder._get_system_prompt("quiz")
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"""다음 참고 자료를 바탕으로 무역 신입사원을 위한 퀴즈를 1개 생성해주세요.

{context}

퀴즈 형식:
1. 문제: 실무 상황을 포함한 구체적인 질문
2. 선택지: 4개 (A, B, C, D)
3. 정답: 정답 선택지
4. 해설: 정답에 대한 상세한 설명
5. 실무 팁: 실제 업무에서 주의할 점

JSON 형식으로 응답해주세요:
{{
  "question": "문제",
  "choices": {{
    "A": "선택지 A",
    "B": "선택지 B",
    "C": "선택지 C",
    "D": "선택지 D"
  }},
  "answer": "정답 (A/B/C/D)",
  "explanation": "해설",
  "tip": "실무 팁"
}}
""")
        ]
        
        try:
            response = self.llm.invoke(messages)
            quiz_text = response.content
            
            return {
                "response": quiz_text,
                "quiz_data": quiz_text,
                "metadata": {
                    "retrieved_docs": len(retrieved_docs),
                    "quiz_mode": "generated"
                }
            }
        except Exception as e:
            return {
                "response": f"퀴즈 생성 중 오류가 발생했습니다: {str(e)}",
                "metadata": {"error": str(e)}
            }
    
    @traceable(name="evaluate_answer")
    def _evaluate_answer(self, user_answer: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate user's answer to a quiz"""
        quiz_data = context.get("quiz_data", {})
        correct_answer = quiz_data.get("answer", "")
        
        # Simple evaluation
        is_correct = user_answer.upper().strip() == correct_answer.upper().strip()
        
        if is_correct:
            response = f"""✓ 정답입니다!

**해설**: {quiz_data.get('explanation', '')}

**실무 팁**: {quiz_data.get('tip', '')}
"""
        else:
            response = f"""✗ 오답입니다.

**정답**: {correct_answer}

**해설**: {quiz_data.get('explanation', '')}

**실무 팁**: {quiz_data.get('tip', '')}
"""
        
        return {
            "response": response,
            "metadata": {
                "is_correct": is_correct,
                "user_answer": user_answer,
                "correct_answer": correct_answer
            }
        }


def main():
    """Test quiz agent"""
    print("=" * 60)
    print("Quiz Agent Test")
    print("=" * 60)
    
    agent = QuizAgent()
    
    # Generate quiz
    result = agent.run("BL에 대한 퀴즈를 내줘")
    
    print("\n" + result["response"])


if __name__ == "__main__":
    main()
