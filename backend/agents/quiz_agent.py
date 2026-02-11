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

class QuizAgent:
    """
    QuizAgent class for generating training quizzes and evaluating answers.
    """
    agent_type: str = "quiz"
    system_prompt: str = "" # To store the loaded system prompt

    def __init__(self):
        self.system_prompt = _load_prompt("quiz_prompt.txt")

    def run(self, user_input: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generates a training quiz or evaluates an answer based on user input and context.
        This is a stub implementation. Real logic will involve LLM calls and RAG.

        Args:
            user_input (str): The user's request (e.g., "Start a quiz on Incoterms, easy level")
                              or their answer to a quiz question.
            context (Dict[str, Any]): Additional context, potentially including RAG results
                                       (e.g., quiz questions, correct answers, difficulty settings).

        Returns:
            Dict[str, Any]: A dictionary containing the agent's response, type, and metadata.
                            {
                                "response": str,       # user-facing message
                                "agent_type": str,     # "quiz"
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
        
        # Simple logic to distinguish between quiz start and answer
        if "퀴즈" in user_input or "문제" in user_input or "시작" in user_input:
            simulated_response = "무역 용어 퀴즈가 생성되었습니다. 다음 질문에 답해주세요."
            simulated_question = "FOB에서 운임은 누가 부담합니까?"
            simulated_choices = ["수출자", "수입자", "포워더", "선사"]
            simulated_answer = "수출자"
            simulated_explanation = "FOB(Free On Board) 조건에서 수출자는 지정된 선적항에서 물품을 본선에 선적할 때까지의 모든 비용과 위험을 부담합니다."
            simulated_quiz_state = "question_generated"
        else: # Assuming user_input is an answer
            simulated_response = "답변을 평가했습니다. 다음은 피드백입니다."
            simulated_question = context.get("question", "알 수 없는 질문")
            simulated_choices = context.get("choices", [])
            simulated_correct_answer = context.get("correct_answer", "알 수 없음")
            is_correct = "수출자" in user_input # Very simple check for stub
            if is_correct:
                simulated_explanation = "정답입니다! FOB 조건에서 수출자가 운임을 부담합니다."
            else:
                simulated_explanation = f"오답입니다. 정답은 '{simulated_correct_answer}'입니다. FOB 조건에서 수출자는 지정된 선적항에서 물품을 본선에 선적할 때까지의 모든 비용과 위험을 부담합니다."
            simulated_quiz_state = "answer_evaluated"


        metadata = {
            "question": simulated_question,
            "choices": simulated_choices,
            "answer": simulated_answer if "quiz_state" not in locals() else simulated_correct_answer,
            "explanation": simulated_explanation,
            "quiz_state": simulated_quiz_state,
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
    # Simple test for QuizAgent stub
    quiz_agent = QuizAgent()
    
    # Test case 1: Start quiz
    test_user_input_start = "인코텀즈 퀴즈 쉬운 난이도로 시작해줘."
    test_context_start = {
        "topic": "Incoterms",
        "difficulty": "easy"
    }
    result_start = quiz_agent.run(test_user_input_start, test_context_start)
    
    print("--- Quiz Agent Start Test Result ---")
    print(f"Response: {result_start['response']}")
    print(f"Agent Type: {result_start['agent_type']}")
    print(f"Metadata: ")
    for key, value in result_start['metadata'].items():
        if key == "llm_input_prepared":
            print(f"  {key}:")
            print(f"    System Prompt (start): {value['system_prompt'][:100]}...")
            print(f"    User Input: {value['user_input']}")
            print(f"    Context: {value['context']}")
        else:
            print(f"  {key}: {value}")
    
    assert result_start['agent_type'] == "quiz"
    assert "퀴즈가 생성되었습니다" in result_start['response']
    assert result_start['metadata']['quiz_state'] == "question_generated"
    assert "System prompt loaded from file" in result_start['response']
    print("\nQuiz Agent start stub test passed!")

    # Test case 2: Evaluate answer
    test_user_input_answer = "수출자"
    test_context_answer = {
        "question": "FOB에서 운임은 누가 부담합니까?",
        "choices": ["수출자", "수입자", "포워더", "선사"],
        "correct_answer": "수출자",
        "quiz_id": "incoterms_q1"
    }
    result_answer = quiz_agent.run(test_user_input_answer, test_context_answer)

    print("\n--- Quiz Agent Answer Test Result ---")
    print(f"Response: {result_answer['response']}")
    print(f"Agent Type: {result_answer['agent_type']}")
    print(f"Metadata: ")
    for key, value in result_answer['metadata'].items():
        if key == "llm_input_prepared":
            print(f"  {key}:")
            print(f"    System Prompt (start): {value['system_prompt'][:100]}...")
            print(f"    User Input: {value['user_input']}")
            print(f"    Context: {value['context']}")
        else:
            print(f"  {key}: {value}")
    
    assert result_answer['agent_type'] == "quiz"
    assert "답변을 평가했습니다" in result_answer['response']
    assert result_answer['metadata']['quiz_state'] == "answer_evaluated"
    assert "정답입니다!" in result_answer['metadata']['explanation']
    assert "System prompt loaded from file" in result_answer['response']
    print("\nQuiz Agent answer stub test passed!")