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
    print(prompt_file_name)
class CEOAgent:
    """
    CEOAgen class for simulating executive decision-making.
    """
    agent_type: str = "ceo"
    system_prompt: str = "" # To store the loaded system prompt

    def __init__(self):
        self.system_prompt = _load_prompt("ceo_prompt.txt")

    def run(self, user_input: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Simulates executive decision-making based on the provided user input and context.
        This is a stub implementation. Real logic will involve LLM calls and RAG.

        Args:
            user_input (str): The user's query or description of the situation.
            context (Dict[str, Any]): Additional context for decision-making,
                                       potentially including RAG results, user profile, etc.

        Returns:
            Dict[str, Any]: A dictionary containing the agent's response, type, and metadata.
                            {
                                "response": str,       # user-facing message
                                "agent_type": str,     # "ceo"
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

        simulated_risk_level = context.get("simulated_risk_level", "medium")
        simulated_decision = context.get("simulated_decision", "Evaluate all long-term impacts.")
        simulated_reasoning = context.get("simulated_reasoning", "Maintaining stakeholder relationships is crucial for sustained growth.")

        metadata = {
            "risk_level": simulated_risk_level,
            "decision": simulated_decision,
            "reasoning": simulated_reasoning,
            "llm_input_prepared": llm_input, # Include prepared LLM input for debugging/traceability
            "processed_input": user_input # Include processed input for debugging
        }

        response_message = f"CEO 관점에서 현재 상황 '{user_input[:50]}...'에 대한 의사결정 시뮬레이션 결과입니다. " \
                           f"주요 결정: '{simulated_decision}'. 리스크 레벨: {simulated_risk_level}." \
                           f"\n(System prompt loaded from file and LLM input structured.)"

        return {
            "response": response_message,
            "agent_type": self.agent_type,
            "metadata": metadata
        }

if __name__ == '__main__':
    # Simple test for CEOAgent stub
    ceo_agent = CEOAgent()
    
    test_user_input = "선적 지연으로 클레임이 발생했습니다. 손실을 최소화하는 방안을 찾아주세요."
    test_context = {
        "current_situation": "shipment_delay_claim",
        "relevant_kpis": {"delay_penalty_rate": "high"},
        "simulated_risk_level": "high",
        "simulated_decision": "Prioritize client relationship over immediate cost savings."
    }
    
    result = ceo_agent.run(test_user_input, test_context)
    
    print("--- CEO Agent Test Result ---")
    print(f"Response: {result['response']}")
    print(f"Agent Type: {result['agent_type']}")
    print(f"Metadata: ")
    for key, value in result['metadata'].items():
        if key == "llm_input_prepared": # Print prepared LLM input nicely
            print(f"  {key}:")
            print(f"    System Prompt (start): {value['system_prompt'][:100]}...")
            print(f"    User Input: {value['user_input']}")
            print(f"    Context: {value['context']}")
        else:
            print(f"  {key}: {value}")
    
    assert result['agent_type'] == "ceo"
    assert "CEO 관점에서" in result['response']
    assert isinstance(result['metadata'], dict)
    assert "System prompt loaded from file" in result['response']
    print("\nCEO Agent stub test passed!")