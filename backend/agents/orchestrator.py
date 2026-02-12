import os
import sys
import json
from typing import Dict, Any, List, Optional
import openai # Import openai
from openai import OpenAI # Import OpenAI client

# Ensure backend directory is in path for imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from backend.config import get_settings

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
        self.settings = get_settings()

        if not self.settings.upstage_api_key:
            print("Warning: UPSTAGE_API_KEY is not set. LLM calls for intent detection will fail.")
            self.llm = None
        else:
            self.llm = OpenAI(
                base_url="https://api.upstage.ai/v1",
                api_key=self.settings.upstage_api_key
            )
        
        # Configure Langsmith tracing
        if self.settings.langsmith_tracing and self.settings.langsmith_api_key:
            os.environ["LANGCHAIN_TRACING_V2"] = "true"
            os.environ["LANGCHAIN_API_KEY"] = self.settings.langsmith_api_key
            os.environ["LANGCHAIN_PROJECT"] = self.settings.langsmith_project
        else:
            os.environ["LANGCHAIN_TRACING_V2"] = "false"

    def run(self, user_input: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Analyzes user input to determine intent, decides which agent to call,
        and returns routing result in metadata.
        Uses Upstage Solar Pro2 LLM for intent detection.

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

        # --- Prepare LLM Messages for Intent Detection ---
        messages = [
            {"role": "system", "content": self.system_prompt}
        ]
        
        llm_user_message_content = f"사용자 입력: {user_input}"
        if context:
            llm_user_message_content += f"\n추가 컨텍스트: {json.dumps(context, ensure_ascii=False)}"
        
        # Define the expected JSON format for intent detection
        intent_json_format = {
            "detected_intent": "quiz | email_coach | mistake_predict | ceo_sim | general_chat | out_of_scope",
            "selected_agent": "QuizAgent | EmailAgent | MistakeAgent | CEOAgent | None",
            "reasoning": "string"
        }
        llm_user_message_content += f"\n\n사용자 입력과 컨텍스트를 분석하여, 다음 JSON 형식에 맞춰 핵심 의도(detected_intent)와 라우팅할 에이전트(selected_agent)를 판단하고, 그 이유를 설명해주세요. \n응답은 반드시 JSON 형식이어야 합니다:\n{json.dumps(intent_json_format, indent=2, ensure_ascii=False)}"
        
        messages.append({"role": "user", "content": llm_user_message_content})

        # --- LLM Call for Intent Detection ---
        detected_intent = "general_chat"
        selected_agent = "None (General Chat)"
        orchestrator_response_prefix = "오케스트레이터가 사용자 의도를 파악하고 있습니다."
        model_used = "solar-pro2"
        llm_output_details = {}
        final_response_message = ""
        
        if self.llm:
            try:
                chat_completion = self.llm.chat.completions.create(
                    model=model_used,
                    messages=messages,
                    temperature=0.3,
                    response_format={"type": "json_object"} # Expect JSON output
                )
                llm_response_content = chat_completion.choices[0].message.content
                
                try:
                    parsed_llm_response = json.loads(llm_response_content)
                    detected_intent = parsed_llm_response.get("detected_intent", "general_chat")
                    selected_agent = parsed_llm_response.get("selected_agent", "None (General Chat)")
                    reasoning = parsed_llm_response.get("reasoning", "LLM based intent detection.")
                    
                    final_response_message = f"오케스트레이터가 의도 '{detected_intent}'를 감지하고 '{selected_agent}' 에이전트로 라우팅합니다. (이유: {reasoning})"
                    llm_output_details = parsed_llm_response
                    
                except json.JSONDecodeError:
                    print(f"Warning: LLM response for intent detection was not valid JSON. Response: {llm_response_content[:100]}...")
                    final_response_message = f"의도 감지 LLM이 유효하지 않은 JSON을 반환했습니다. 원본 응답: {llm_response_content[:100]}..."
                    llm_output_details = {"raw_llm_response": llm_response_content}
                
            except openai.APIError as e:
                print(f"Upstage API Error during intent detection: {e}")
                final_response_message = f"LLM API 호출 중 오류가 발생하여 의도 감지에 실패했습니다: {e}"
                llm_output_details = {"error": str(e)}
            except Exception as e:
                print(f"An unexpected error occurred during LLM intent detection: {e}")
                final_response_message = f"LLM 의도 감지 중 예상치 못한 오류가 발생했습니다: {e}"
                llm_output_details = {"error": str(e)}
        else:
            final_response_message = "LLM 클라이언트가 초기화되지 않아 의도 감지를 수행할 수 없습니다. UPSTAGE_API_KEY를 확인하세요."
            llm_output_details = {"error": "LLM client not initialized due to missing API key."}


        metadata = {
            "routing_info": {
                "detected_intent": detected_intent,
                "selected_agent": selected_agent
            },
            "model": model_used,
            "llm_input_prepared": messages,
            "llm_output_details": llm_output_details,
            "input_context": context,
            "processed_input": user_input
        }

        return {
            "response": final_response_message,
            "agent_type": self.agent_type,
            "metadata": metadata
        }

if __name__ == '__main__':
    settings = get_settings()
    if not settings.upstage_api_key:
        print("UPSTAGE_API_KEY is not set in your .env file. LLM calls for intent detection will be skipped.")
    if settings.langsmith_tracing and not settings.langsmith_api_key:
        print("LANGSMITH_API_KEY is not set. Langsmith tracing will be disabled.")
    
    print("--- Orchestrator Agent Test with real LLM for Intent Detection ---")
    orchestrator_agent = OrchestratorAgent()
    
    test_cases = [
        ("선적 지연에 대해 CEO의 의견을 듣고 싶습니다.", {"urgent": True}),
        ("선적 지연 이메일을 작성해 주세요.", {"recipient": "client"}),
        ("BL 작성 시 주의할 점은 무엇인가요?", {}),
        ("무역 용어 퀴즈를 풀어볼까요?", {"difficulty": "easy"}),
        ("안녕하세요, 시스템 동작 테스트 중입니다.", {}),
        ("날씨가 어때요?", {}) # Out of scope or general chat
    ]

    for user_input, context in test_cases:
        print(f"\n--- Orchestrator Agent Test for: '{user_input}' ---")
        
        print(f"Running with UPSTAGE_API_KEY: {'*****' + settings.upstage_api_key[-4:] if settings.upstage_api_key else 'Not Set'}")
        print(f"Langsmith Tracing: {settings.langsmith_tracing and bool(settings.langsmith_api_key)}")

        result = orchestrator_agent.run(user_input, context)
        
        print(f"Response: {result['response']}")
        print(f"Agent Type: {result['agent_type']}")
        print(f"Metadata: {json.dumps(result['metadata'], indent=2, ensure_ascii=False)}")
        
        assert result['agent_type'] == "orchestrator"
        assert isinstance(result['response'], str)
        assert isinstance(result['metadata'], dict)
        assert result['metadata']['model'] == "solar-pro2"
        assert "llm_input_prepared" in result['metadata']
    
    print("\nOrchestrator Agent integration test passed (if API key was valid and call succeeded)!")