import os
import sys
import json
from typing import Dict, Any, List, Optional

# Ensure backend directory is in path for imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

# No direct RAG/LLM calls for Orchestrator's *response generation* in this stub,
# but it orchestrates agents that might use them.
# For intent detection, an LLM call would be used here later.

def _load_prompt(prompt_file_name: str) -> str:
    """
    Loads a prompt text from the specified file name.
    Assumes prompt files are in backend/prompts/ relative to the project root.
    """
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(current_dir, '..', '..'))
    prompt_path = os.path.join(project_root, 'backend', 'prompts', prompt_file_name)
    
    if not os.path.exists(prompt_path):
        raise FileNotFoundError(f"Prompt file not found: {prompt_path}")
        
    with open(prompt_path, 'r', encoding='utf-8') as f:
        return f.read()

class OrchestratorAgent:
    """
    OrchestratorAgent class for analyzing user input, routing to appropriate agents,
    and combining/managing responses. Acts as the system brain.
    """
    agent_type: str = "orchestrator"
    system_prompt: str = ""

    def __init__(self):
        self.system_prompt = _load_prompt("orchestrator.txt")

    def run(self, user_input: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Analyzes user input to determine intent, decides which agent to call,
        and returns routing result in metadata.
        This is a stub implementation. Real logic will involve LLM-based intent detection,
        calling sub-agents, and merging their responses.

        Args:
            user_input (str): The user's query or request.
            context (Optional[Dict[str, Any]]): Additional context, conversation history, etc.

        Returns:
            Dict[str, Any]: A dictionary containing the agent's response, type, and metadata.
                            {
                                "response": str,       # user-facing message
                                "agent_type": str,     # "orchestrator"
                                "metadata": dict       # structured extra data
                            }
        """
        if context is None:
            context = {}

        # --- Intent Detection Stub ---
        # In a real implementation, an LLM call would analyze user_input + context
        # against the system_prompt to determine the intent and routed agent.
        # It would parse LLM output (JSON) for detected_intent and parameters.
        # For now, we use a simple keyword-based stub for intent detection.
        
        detected_intent = "general_chat"
        selected_agent = "None (General Chat)"
        response_message_prefix = "일반 채팅 에이전트로 라우팅합니다."

        if "CEO" in user_input.upper() or "대표" in user_input or "의사결정" in user_input:
            detected_intent = "ceo_sim"
            selected_agent = "CEOAgen"
            response_message_prefix = "CEO 에이전트로 라우팅합니다."
        elif "이메일" in user_input or "메일" in user_input or "작성" in user_input or "분석" in user_input:
            detected_intent = "email_coach"
            selected_agent = "EmailAgent"
            response_message_prefix = "이메일 에이전트로 라우팅합니다."
        elif "실수" in user_input or "주의할 점" in user_input or "경고" in user_input:
            detected_intent = "mistake_predict"
            selected_agent = "MistakeAgent"
            response_message_prefix = "실수 예측 에이전트로 라우팅합니다."
        elif "퀴즈" in user_input or "문제" in user_input or "시험" in user_input or "트레이닝" in user_input:
            detected_intent = "quiz"
            selected_agent = "QuizAgent"
            response_message_prefix = "퀴즈 에이전트로 라우팅합니다."
        
        # --- End Intent Detection Stub ---

        # Prepare LLM input structure (for potential intent detection LLM call)
        llm_input_prepared_for_intent_detection = {
            "system_prompt": self.system_prompt,
            "user_query": user_input,
            "current_context": context,
            "possible_intents": ["ceo_sim", "email_coach", "mistake_predict", "quiz", "general_chat", "out_of_scope"]
        }

        metadata = {
            "routing_info": {
                "detected_intent": detected_intent,
                "selected_agent": selected_agent
            },
            "llm_input_prepared_for_intent_detection": llm_input_prepared_for_intent_detection, # For debugging
            "input_context": context,
            "processed_input": user_input
        }

        response_message = f"{response_message_prefix} 사용자 질의 '{user_input[:50]}...'에 대해 '{selected_agent}' 에이전트로 처리를 준비 중입니다." \
                           f" (System prompt loaded from file and LLM input structured for intent detection.)"

        return {
            "response": response_message,
            "agent_type": self.agent_type,
            "metadata": metadata
        }

if __name__ == '__main__':
    print("--- Orchestrator Agent Test ---")
    orchestrator_agent = OrchestratorAgent()
    
    test_cases = [
        ("선적 지연에 대해 CEO의 의견을 듣고 싶습니다.", {}),
        ("선적 지연 이메일을 작성해 주세요.", {"recipient": "client"}),
        ("BL 작성 시 주의할 점은 무엇인가요?", {}),
        ("무역 용어 퀴즈를 풀어볼까요?", {"difficulty": "easy"}),
        ("안녕하세요, 시스템 동작 테스트 중입니다.", {}),
        ("날씨가 어때요?", {}) # Out of scope or general chat
    ]

    for user_input, context in test_cases:
        print(f"\n--- Orchestrator Agent Test for: '{user_input}' ---")
        result = orchestrator_agent.run(user_input, context)
        
        print(f"Response: {result['response']}")
        print(f"Agent Type: {result['agent_type']}")
        print(f"Metadata: ")
        for key, value in result['metadata'].items():
            if key == "llm_input_prepared_for_intent_detection":
                print(f"  {key}:")
                print(f"    System Prompt (start): {value['system_prompt'][:100]}...")
                print(f"    User Query: {value['user_query']}")
                print(f"    Current Context: {value['current_context']}")
                print(f"    Possible Intents: {value['possible_intents']}")
            else:
                print(f"  {key}: {value}")
        
        assert result['agent_type'] == "orchestrator"
        assert isinstance(result['metadata'], dict)
        assert "System prompt loaded from file" in result['response']
    
    print("\nOrchestrator Agent stub tests passed!")
