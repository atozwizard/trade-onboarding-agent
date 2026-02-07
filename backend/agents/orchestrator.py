"""
Agent Orchestrator - Intent detection and routing to appropriate agents
"""

import os
from typing import Dict, Any, Optional
from dotenv import load_dotenv
from langchain_upstage import ChatUpstage
from langsmith import traceable

load_dotenv()


class AgentOrchestrator:
    """
    Orchestrates requests to appropriate agents based on intent detection
    """
    
    def __init__(self):
        self.llm = ChatUpstage(
            model="solar-pro-preview-240910",
            api_key=os.getenv("UPSTAGE_API_KEY")
        )
        
        # Import agents (lazy loading to avoid circular imports)
        self.agents = {}
    
    def register_agent(self, agent_type: str, agent):
        """Register an agent"""
        self.agents[agent_type] = agent
    
    @traceable(name="detect_intent")
    def detect_intent(self, user_input: str) -> str:
        """
        Detect user intent from input
        
        Args:
            user_input: User's message
        
        Returns:
            Agent type: quiz, email, ceo, mistake, or general
        """
        # Keyword-based intent detection
        user_input_lower = user_input.lower()
        
        # Quiz keywords
        if any(keyword in user_input_lower for keyword in ["퀴즈", "quiz", "문제", "테스트", "시험"]):
            return "quiz"
        
        # Email keywords
        if any(keyword in user_input_lower for keyword in ["메일", "email", "이메일", "편지"]):
            return "email"
        
        # CEO simulator keywords
        if any(keyword in user_input_lower for keyword in ["보고", "대표", "ceo", "사장", "report"]):
            return "ceo"
        
        # Mistake predictor keywords
        if any(keyword in user_input_lower for keyword in ["실수", "mistake", "오류", "주의", "체크"]):
            return "mistake"
        
        # Default to general
        return "general"
    
    @traceable(name="route_agent")
    def route(self, user_input: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Route user input to appropriate agent
        
        Args:
            user_input: User's message
            context: Optional context (conversation history, user data, etc.)
        
        Returns:
            Agent response
        """
        # Detect intent
        intent = self.detect_intent(user_input)
        
        # Get appropriate agent
        agent = self.agents.get(intent)
        
        if not agent:
            return {
                "agent_type": "general",
                "response": "죄송합니다. 해당 요청을 처리할 수 없습니다.",
                "metadata": {"intent": intent}
            }
        
        # Execute agent
        try:
            response = agent.run(user_input, context)
            response["agent_type"] = intent
            return response
        except Exception as e:
            return {
                "agent_type": intent,
                "response": f"오류가 발생했습니다: {str(e)}",
                "metadata": {"error": str(e)}
            }
    
    def get_agent_info(self) -> Dict[str, str]:
        """Get information about available agents"""
        return {
            "quiz": "퀴즈 생성 및 평가 에이전트",
            "email": "이메일 작성 코칭 에이전트",
            "ceo": "대표 시뮬레이터 에이전트",
            "mistake": "실수 예측 에이전트",
            "general": "일반 질의응답 에이전트"
        }


def main():
    """Test orchestrator"""
    orchestrator = AgentOrchestrator()
    
    # Test intent detection
    test_inputs = [
        "퀴즈 하나 내줘",
        "이메일 작성 도와줘",
        "대표님께 보고 연습하고 싶어",
        "이 상황에서 실수할 수 있는 게 뭐야?",
        "BL이 뭐야?"
    ]
    
    print("=" * 60)
    print("Agent Orchestrator - Intent Detection Test")
    print("=" * 60)
    
    for user_input in test_inputs:
        intent = orchestrator.detect_intent(user_input)
        print(f"\nInput: {user_input}")
        print(f"Intent: {intent}")


if __name__ == "__main__":
    main()
