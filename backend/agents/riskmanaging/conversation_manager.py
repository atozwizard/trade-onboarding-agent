# backend/agents/riskmanaging/conversation_manager.py

import json
from typing import List, Dict, Any, Optional
import openai
from openai import OpenAI
from langsmith import traceable
import os

from backend.config import get_settings
from backend.agents.riskmanaging.prompt_loader import CONVERSATION_ASSESSMENT_PROMPT
from backend.agents.riskmanaging.schemas import RiskManagingAgentInput # Assuming this schema for consistent input

class ConversationManager:
    def __init__(self):
        self.settings = get_settings()
        if not self.settings.upstage_api_key:
            print("Warning: UPSTAGE_API_KEY is not set. LLM calls for ConversationManager will fail.")
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

    @traceable(name="conversation_manager_assess")
    def assess_conversation_progress(self, agent_input: RiskManagingAgentInput) -> Dict[str, Any]:
        """
        Assesses if enough information is gathered to proceed with risk analysis.
        If not, it generates follow-up questions.

        Args:
            agent_input (RiskManagingAgentInput): Current user input and conversation history.

        Returns:
            Dict[str, Any]: A dictionary containing status ("sufficient" or "insufficient"),
                            a message, analysis_ready flag, and optionally follow_up_questions.
        """
        if not self.llm:
            return {
                "status": "error",
                "message": "LLM 클라이언트가 초기화되지 않았습니다. API 키를 확인하세요.",
                "analysis_ready": False
            }
        
        conversation_history_str = ""
        if agent_input.conversation_history:
            for turn in agent_input.conversation_history:
                conversation_history_str += f"{turn.get('role', 'User')}: {turn.get('content', '')}\n" # Corrected line (explicit \n)

        # Prepare messages for the LLM
        messages = [
            {"role": "system", "content": CONVERSATION_ASSESSMENT_PROMPT.split("<대화 내용>")[0]}, # System part of the prompt
            {"role": "user", "content": CONVERSATION_ASSESSMENT_PROMPT.format(
                conversation_history=conversation_history_str,
                user_input=agent_input.user_input
            )}
        ]
        
        try:
            chat_completion = self.llm.chat.completions.create(
                model="solar-pro2",
                messages=messages,
                temperature=0.1, # Keep temperature low for structured output
                response_format={"type": "json_object"}
            )
            llm_response_content = chat_completion.choices[0].message.content
            
            parsed_response = json.loads(llm_response_content)
            return parsed_response

        except openai.APIError as e:
            print(f"Upstage API Error during conversation assessment: {e}")
            return {
                "status": "error",
                "message": f"LLM API 호출 중 오류가 발생했습니다: {e}",
                "analysis_ready": False
            }
        except json.JSONDecodeError as e:
            print(f"Failed to parse LLM response as JSON in ConversationManager: {llm_response_content[:500]}... Error: {e}")
            return {
                "status": "error",
                "message": f"LLM 응답 파싱 오류: {e}. 응답: {llm_response_content}",
                "analysis_ready": False
            }
        except Exception as e:
            print(f"An unexpected error occurred in ConversationManager: {e}")
            return {
                "status": "error",
                "message": f"대화 진행 평가 중 예상치 못한 오류 발생: {e}",
                "analysis_ready": False
            }

# Example Usage (for testing)
if __name__ == '__main__':
    settings = get_settings()
    if not settings.upstage_api_key:
        print("UPSTAGE_API_KEY is not set. ConversationManager will not function properly.")
        exit()

    cm = ConversationManager()

    print("\n--- Conversation Manager Test: Insufficient Info ---")
    input_insufficient = RiskManagingAgentInput(
        user_input="우리 회사에 문제가 발생했어.",
        conversation_history=[]
    )
    result_insufficient = cm.assess_conversation_progress(input_insufficient)
    print(json.dumps(result_insufficient, indent=2, ensure_ascii=False))

    print("\n--- Conversation Manager Test: Sufficient Info ---")
    input_sufficient = RiskManagingAgentInput(
        user_input="해외 계약 진행 중 고객사가 갑자기 payment terms 변경을 요청했어. 납기 지연 가능성도 있어.",
        conversation_history=[
            {"role": "Agent", "content": "어떤 계약 건인지, 계약 규모는 어느 정도인지 알려주시겠습니까?"},
            {"role": "User", "content": "대규모 선적 계약 건이고, 총 10만 달러 규모입니다. 다음 주까지 선적 완료 예정이었습니다."}
        ]
    )
    result_sufficient = cm.assess_conversation_progress(input_sufficient)
    print(json.dumps(result_sufficient, indent=2, ensure_ascii=False))