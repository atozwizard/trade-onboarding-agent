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

class MistakeAgent:
    """
    MistakeAgent class for detecting possible employee mistakes and providing guidance.
    """
    agent_type: str = "mistake"
    system_prompt: str = "" # To store the loaded system prompt

    def __init__(self):
        self.system_prompt = _load_prompt("mistake_prompt.txt")

    def run(self, user_input: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Detects possible employee mistakes based on user input and context,
        and provides explanations and prevention strategies.
        This is a stub implementation. Real logic will involve LLM calls and RAG.

        Args:
            user_input (str): The user's description of a situation or a request for mistake analysis.
            context (Dict[str, Any]): Additional context, potentially including RAG results
                                       (e.g., common mistake patterns, internal process documents).

        Returns:
            Dict[str, Any]: A dictionary containing the agent's response, type, and metadata.
                            {
                                "response": str,       # user-facing message
                                "agent_type": str,     # "mistake"
                                "metadata": dict       # structured extra data
                            }
        """
        # Prepare LLM input structure
        llm_input = {
            "system_prompt": self.system_prompt,
            "user_input": user_input,
            "context": context
        }

        # --- LLM Call Stub ---
        # In a real implementation, this would involve calling an LLM API
        # with llm_input and parsing its JSON response.
        # For now, we simulate a response based on the previous stub logic.
        
        simulated_mistakes = ["BL date mismatch", "HS code error"]
        simulated_risk_level = "high"
        simulated_coaching_point = "Always double-check critical document fields."
        simulated_explanation = "BL 날짜 불일치나 HS 코드 오류는 통관 지연 및 벌금으로 이어질 수 있어 회사에 큰 재정적 손실을 입히고 거래처와의 신뢰 관계를 손상시킬 수 있습니다. 이러한 실수는 실무자의 신중한 검토 부족이나 정보 오입력으로 인해 발생하며, 내부적으로는 엄중한 비판을 받을 수 있는 중대한 사안입니다."

        metadata = {
            "mistakes": simulated_mistakes,
            "risk_level": simulated_risk_level,
            "coaching_point": simulated_coaching_point,
            "explanation": simulated_explanation,
            "llm_input_prepared": llm_input, # Include prepared LLM input for debugging/traceability
            "processed_input": user_input
        }

        response_message = f"제시된 상황 '{user_input[:50]}...'에서 발생 가능한 실수와 예방 가이드입니다. " \
                           f"예상되는 실수: {', '.join(simulated_mistakes)}. (System prompt loaded from file and LLM input structured.)"

        return {
            "response": response_message,
            "agent_type": self.agent_type,
            "metadata": metadata
        }

if __name__ == '__main__':
    # Simple test for MistakeAgent stub
    mistake_agent = MistakeAgent()
    
    test_user_input = "선적 서류 작성 중입니다. 어떤 실수를 주의해야 할까요?"
    test_context = {
        "document_type": "BL draft",
        "user_role": "junior",
        "related_process": "documentation_preparation"
    }
    
    result = mistake_agent.run(test_user_input, test_context)
    
    print("--- Mistake Agent Test Result ---")
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
    
    assert result['agent_type'] == "mistake"
    assert "발생 가능한 실수와 예방 가이드입니다" in result['response']
    assert isinstance(result['metadata']['mistakes'], list)
    assert result['metadata']['risk_level'] == "high"
    assert "System prompt loaded from file" in result['response']
    print("\nMistake Agent stub test passed!")