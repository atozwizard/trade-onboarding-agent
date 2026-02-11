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

class EmailAgent:
    """
    EmailAgent class for analyzing business email intent/risk and drafting emails.
    """
    agent_type: str = "email"
    system_prompt: str = "" # To store the loaded system prompt

    def __init__(self):
        self.system_prompt = _load_prompt("email_prompt.txt")

    def run(self, user_input: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyzes business email intent/risk or drafts emails based on user input and context.
        This is a stub implementation. Real logic will involve LLM calls and RAG.

        Args:
            user_input (str): The user's query (e.g., "Draft an email about shipment delay")
                              or an email draft for analysis.
            context (Dict[str, Any]): Additional context, potentially including RAG results,
                                       recipient info, desired tone, etc.

        Returns:
            Dict[str, Any]: A dictionary containing the agent's response, type, and metadata.
                            {
                                "response": str,       # user-facing message
                                "agent_type": str,     # "email"
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
        
        # Determine if the user wants an email drafted or an email analyzed
        if "draft" in user_input.lower() or "써줘" in user_input:
            simulated_response = "이메일 초안이 작성되었습니다. 상황과 수신자에 맞춰 수정해 주세요."
            simulated_risk_signals = ["None"]
            simulated_urgency = "normal"
            simulated_intent = "draft_email"
            simulated_email_content = f"제목: [Draft] {context.get('email_subject', '문의')}\n\n" \
                                      f"내용: {user_input}에 대한 이메일입니다."
        else:
            simulated_response = "제공된 이메일에 대한 리스크 분석 결과입니다."
            simulated_risk_signals = ["hidden_dissatisfaction", "negotiation_pressure"]
            simulated_urgency = "high"
            simulated_intent = "analyze_email"
            simulated_email_content = f"분석 대상: {user_input}"

        metadata = {
            "risk_signals": simulated_risk_signals,
            "urgency": simulated_urgency,
            "intent": simulated_intent,
            "analysis_details": "가상 분석입니다. 실제 LLM이 더 자세히 분석합니다.",
            "simulated_email_content": simulated_email_content,
            "llm_input_prepared": llm_input, # Include prepared LLM input for debugging/traceability
            "processed_input": user_input
        }

        response_message = f"{simulated_response} (System prompt loaded from file and LLM input structured.)"

        return {
            "response": response_message,
            "agent_type": self.agent_type,
            "metadata": metadata
        }

if __name__ == '__main__':
    # Simple test for EmailAgent stub
    email_agent = EmailAgent()
    
    # Test case 1: Draft email
    test_user_input_draft = "선적 지연에 대해 거래처에 보낼 이메일을 써줘."
    test_context_draft = {
        "email_subject": "선적 지연 통보",
        "recipient_type": "Client",
        "delay_reason": "악천후"
    }
    result_draft = email_agent.run(test_user_input_draft, test_context_draft)
    
    print("--- Email Agent Draft Test Result ---")
    print(f"Response: {result_draft['response']}")
    print(f"Agent Type: {result_draft['agent_type']}")
    print(f"Metadata: ")
    for key, value in result_draft['metadata'].items():
        if key == "llm_input_prepared":
            print(f"  {key}:")
            print(f"    System Prompt (start): {value['system_prompt'][:100]}...")
            print(f"    User Input: {value['user_input']}")
            print(f"    Context: {value['context']}")
        else:
            print(f"  {key}: {value}")
    
    assert result_draft['agent_type'] == "email"
    assert "이메일 초안이 작성되었습니다" in result_draft['response']
    assert result_draft['metadata']['intent'] == "draft_email"
    print("\nEmail Agent draft stub test passed!")

    # Test case 2: Analyze email
    test_user_input_analyze = "확인 메일: 'Your recent request seems challenging. We need to discuss further.'"
    test_context_analyze = {
        "recipient_type": "Supplier",
        "previous_interaction": "negotiation on price"
    }
    result_analyze = email_agent.run(test_user_input_analyze, test_context_analyze)

    print("\n--- Email Agent Analyze Test Result ---")
    print(f"Response: {result_analyze['response']}")
    print(f"Agent Type: {result_analyze['agent_type']}")
    print(f"Metadata: ")
    for key, value in result_analyze['metadata'].items():
        if key == "llm_input_prepared":
            print(f"  {key}:")
            print(f"    System Prompt (start): {value['system_prompt'][:100]}...")
            print(f"    User Input: {value['user_input']}")
            print(f"    Context: {value['context']}")
        else:
            print(f"  {key}: {value}")
    
    assert result_analyze['agent_type'] == "email"
    assert "리스크 분석 결과입니다" in result_analyze['response']
    assert result_analyze['metadata']['intent'] == "analyze_email"
    assert "hidden_dissatisfaction" in result_analyze['metadata']['risk_signals']
    print("\nEmail Agent analyze stub test passed!")