import os
import sys
import json
from typing import Dict, Any, List, Optional

# Ensure backend directory is in path for imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from backend.config import get_settings
from backend.rag.embedder import get_embedding
from backend.rag.retriever import search as rag_search

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

class QuizAgent:
    """
    QuizAgent class for generating training quizzes and evaluating answers.
    """
    agent_type: str = "quiz"
    system_prompt: str = ""

    def __init__(self):
        self.system_prompt = _load_prompt("quiz_prompt.txt")
        self.settings = get_settings()

    def run(self, user_input: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Generates a training quiz or evaluates an answer based on user input and context.
        Uses RAG to find relevant information and prepares an LLM-ready input structure.

        Args:
            user_input (str): The user's request (e.g., "Start a quiz on Incoterms, easy level")
                              or their answer to a quiz question.
            context (Optional[Dict[str, Any]]): Additional context, potentially including
                                       quiz questions, correct answers, difficulty settings.

        Returns:
            Dict[str, Any]: A dictionary containing the agent's response, type, and metadata.
                            {
                                "response": str,       # user-facing message
                                "agent_type": str,     # "quiz"
                                "metadata": dict       # structured extra data
                            }
        """
        if context is None:
            context = {}

        # --- RAG Search ---
        retrieved_documents = []
        used_rag = False

        try:
            if not self.settings.upstage_api_key:
                raise ValueError("UPSTAGE_API_KEY is not set. Cannot perform RAG search.")

            # Search for relevant quiz samples, trade QA, company domain knowledge based on user_input and context
            rag_query = user_input
            if context.get("topic"):
                rag_query += f" {context['topic']}"
            if context.get("difficulty"):
                rag_query += f" {context['difficulty']}"
            
            rag_results = rag_search(query=rag_query, k=3)

            if rag_results:
                used_rag = True
                retrieved_documents = [{"document": doc["document"], "metadata": doc["metadata"]} for doc in rag_results]

        except ValueError as e:
            print(f"RAG search skipped due to configuration error: {e}")
        except Exception as e:
            print(f"An error occurred during RAG search: {e}")

        # --- Prepare LLM Input ---
        rag_context_str = ""
        if used_rag and retrieved_documents:
            rag_context_str = "\n\n--- 참조 문서 ---\n"
            for i, doc in enumerate(retrieved_documents):
                rag_context_str += f"문서 {i+1} (출처: {doc['metadata'].get('source_dataset', 'unknown')} | 유형: {doc['metadata'].get('document_type', 'unknown')} | 주제: {', '.join(doc['metadata'].get('topic', []))}):\n{doc['document']}\n\n"
        
        llm_user_message = f"사용자 요청: {user_input}"
        if context:
            llm_user_message += f"\n추가 컨텍스트: {json.dumps(context, ensure_ascii=False)}"
        llm_user_message += rag_context_str

        # --- LLM Call Stub (Simulated Response) ---
        if "퀴즈" in user_input or "문제" in user_input or "시작" in user_input:
            simulated_response_text = "무역 용어 퀴즈가 생성되었습니다. 다음 질문에 답해주세요."
            simulated_question = "FOB에서 운임은 누가 부담합니까?"
            simulated_choices = ["수출자", "수입자", "포워더", "선사"]
            simulated_answer = "수출자"
            simulated_explanation = "FOB(Free On Board) 조건에서 수출자는 지정된 선적항에서 물품을 본선에 선적할 때까지의 모든 비용과 위험을 부담합니다."
            simulated_quiz_state = "question_generated"
        else: # Assuming user_input is an answer
            simulated_response_text = "답변을 평가했습니다. 다음은 피드백입니다."
            simulated_question = context.get("question", "알 수 없는 질문")
            simulated_choices = context.get("choices", [])
            simulated_correct_answer = context.get("correct_answer", "알 수 없음")
            is_correct = "수출자" in user_input # Very simple check for stub
            if is_correct:
                simulated_explanation = "정답입니다! FOB 조건에서 수출자가 운임을 부담합니다."
            else:
                simulated_explanation = f"오답입니다. 정답은 '{simulated_correct_answer}'입니다. FOB 조건에서 수출자는 지정된 선적항에서 물품을 본선에 선적할 때까지의 모든 비용과 위험을 부담합니다."
            simulated_quiz_state = "answer_evaluated"


        llm_output_simulation = {
            "quiz_response": simulated_response_text,
            "question": simulated_question,
            "choices": simulated_choices,
            "answer": simulated_answer if "quiz_state" not in locals() or simulated_quiz_state == "question_generated" else simulated_correct_answer,
            "explanation": simulated_explanation,
            "quiz_state": simulated_quiz_state,
            "used_rag_in_llm_simulation": used_rag
        }

        metadata = {
            "used_rag": used_rag,
            "documents": retrieved_documents,
            "llm_input_prepared": llm_user_message,
            "llm_output_simulation": llm_output_simulation,
            "input_context": context,
            "processed_input": user_input
        }

        response_message = f"{llm_output_simulation.get('quiz_response', '퀴즈 에이전트가 응답을 생성했습니다.')} (System prompt loaded, LLM input structured, RAG: {used_rag})"

        return {
            "response": response_message,
            "agent_type": self.agent_type,
            "metadata": metadata
        }

if __name__ == '__main__':
    settings = get_settings()
    if not settings.upstage_api_key:
        print("UPSTAGE_API_KEY is not set in your .env file. RAG search will be skipped.")

    print("--- Quiz Agent Test ---")
    quiz_agent = QuizAgent()
    
    # Test case 1: Start quiz with RAG
    test_user_input_start = "인코텀즈 퀴즈 쉬운 난이도로 시작해줘."
    test_context_start = {
        "topic": "Incoterms",
        "difficulty": "easy"
    }
    result_start = quiz_agent.run(test_user_input_start, test_context_start)
    
    print("\n--- Quiz Agent Start Test Result ---")
    print(f"Response: {result_start['response']}")
    print(f"Agent Type: {result_start['agent_type']}")
    print(f"Metadata: {json.dumps(result_start['metadata'], indent=2, ensure_ascii=False)}")
    
    assert result_start['agent_type'] == "quiz"
    assert "퀴즈가 생성되었습니다" in result_start['response']
    assert result_start['metadata']['llm_output_simulation']['quiz_state'] == "question_generated"
    print("\nQuiz Agent start stub test passed!")

    # Test case 2: Evaluate answer with RAG
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
    print(f"Metadata: {json.dumps(result_answer['metadata'], indent=2, ensure_ascii=False)}")
    
    assert result_answer['agent_type'] == "quiz"
    assert "답변을 평가했습니다" in result_answer['response']
    assert result_answer['metadata']['llm_output_simulation']['quiz_state'] == "answer_evaluated"
    assert "정답입니다!" in result_answer['metadata']['llm_output_simulation']['explanation']
    print("\nQuiz Agent answer stub test passed!")
