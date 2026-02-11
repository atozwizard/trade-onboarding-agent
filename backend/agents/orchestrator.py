import os
from typing import Dict, Any, List

def _load_prompt(prompt_file_name: str) -> str:
    # Assuming prompt files are in backend/prompts/ relative to the project root
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # Adjust path to project root: current_dir (agents) -> parent (backend) -> parent (project_root)
    project_root = os.path.abspath(os.path.join(current_dir, '..', '..'))
    prompt_path = os.path.join(project_root, 'backend', 'prompts', prompt_file_name) # Prompts are under backend/prompts
    
    if not os.path.exists(prompt_path):
        raise FileNotFoundError(f"Prompt file not found: {prompt_path}")
        
    with open(prompt_path, 'r', encoding='utf-8') as f:
        return f.read()

class OrchestratorAgent:
    """
    OrchestratorAgent class for analyzing user input, routing to appropriate agents,
    and combining/managing responses.
    """
    agent_type: str = "orchestrator"
    system_prompt: str = "" # To store the loaded system prompt

    def __init__(self):
        self.system_prompt = _load_prompt("orchestrator.txt")
        # print(self.system_prompt)
    def run(self, user_input: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyzes user input to determine intent, routes the task to a sub-agent,
        and potentially merges results.
        This is a stub implementation. Real logic will involve intent detection,
        agent calling, and response merging.

        Args:
            user_input (str): The user's query or request.
            context (Dict[str, Any]): Additional context, conversation history, etc.

        Returns:
            Dict[str, Any]: A dictionary containing the agent's response, type, and metadata.
                            {
                                "response": str,       # user-facing message
                                "agent_type": str,     # "orchestrator"
                                "metadata": dict       # structured extra data
                            }
        """
        # Prepare LLM input structure
        llm_input = {
            "system_prompt": self.system_prompt,
            "user_input": user_input,
            "context": context
        }

        # --- LLM Call Stub for Intent Detection ---
        # In a real implementation, an LLM call would analyze user_input + context
        # against the system_prompt to determine the intent and routed agent.
        # For now, we use a simple keyword-based stub for intent detection.
        
        detected_intent = "general_chat"
        routed_agent = "None (General Chat)"
        response_message_prefix = "일반 채팅으로 처리합니다."

        if "CEO" in user_input.upper() or "대표" in user_input or "의사결정" in user_input:
            detected_intent = "ceo_sim"
            routed_agent = "CEOAgen"
            response_message_prefix = "CEO 에이전트로 라우팅합니다."
        elif "이메일" in user_input or "메일" in user_input or "작성" in user_input or "분석" in user_input:
            detected_intent = "email_coach"
            routed_agent = "EmailAgent"
            response_message_prefix = "이메일 에이전트로 라우팅합니다."
        elif "실수" in user_input or "주의할 점" in user_input or "경고" in user_input:
            detected_intent = "mistake_predict"
            routed_agent = "MistakeAgent"
            response_message_prefix = "실수 예측 에이전트로 라우팅합니다."
        elif "퀴즈" in user_input or "문제" in user_input or "시험" in user_input or "트레이닝" in user_input:
            detected_intent = "quiz"
            routed_agent = "QuizAgent"
            response_message_prefix = "퀴즈 에이전트로 라우팅합니다."
        
        # --- End LLM Call Stub ---

        metadata = {
            "routing_info": {
                "detected_intent": detected_intent,
                "selected_agent": routed_agent # Renamed from routed_agent to selected_agent as per requirement
            },
            "llm_input_prepared": llm_input, # Include prepared LLM input for debugging/traceability
            "processed_input": user_input
        }

        response_message = f"{response_message_prefix} 사용자 질의 '{user_input[:50]}...'에 대한 최종 응답을 준비 중입니다. " \
                           f"(System prompt loaded from file and LLM input structured. Routed to: {routed_agent})"

        return {
            "response": response_message,
            "agent_type": self.agent_type,
            "metadata": metadata
        }

if __name__ == '__main__':
    # Simple test for OrchestratorAgent stub
    orchestrator_agent = OrchestratorAgent()
    
    test_cases = [
        ("선적 지연에 대해 CEO의 의견을 듣고 싶습니다.", {}),
        ("선적 지연 이메일을 작성해 주세요.", {}),
        ("BL 작성 시 주의할 점은 무엇인가요?", {}),
        ("무역 용어 퀴즈를 풀어볼까요?", {}),
        ("안녕하세요, 시스템 동작 테스트 중입니다.", {})
    ]

    for user_input, context in test_cases:
        print(f"\n--- Orchestrator Agent Test for: '{user_input}' ---")
        result = orchestrator_agent.run(user_input, context)
        
        print(f"Response: {result['response']}")
        print(f"Agent Type: {result['agent_type']}")
        print(f"Metadata: ")
        for key, value in result['metadata'].items():
            if key == "llm_input_prepared":
                print(f"  {key}:")
                print(f"    System Prompt (start): {value['system_prompt'][:100]}...")
                print(f"    User Input: {value['user_input']}")
                print(f"    Context: {value['context']}")
            else:
                print(f"  {key}: {value}")
        
        assert result['agent_type'] == "orchestrator"
        assert isinstance(result['metadata'], dict)
        assert "System prompt loaded from file" in result['response']
    
    print("\nOrchestrator Agent stub tests passed!")