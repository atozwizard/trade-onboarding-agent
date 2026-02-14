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

    def _check_analysis_ready(self, extracted_data: Dict[str, Any]) -> bool:
        score = 0

        if extracted_data.get("contract_amount"):
            score += 1
        if extracted_data.get("penalty_info"):
            score += 1
        if extracted_data.get("loss_estimate"):
            score += 1
        if extracted_data.get("delay_days") or extracted_data.get("delay_risk"):
            score += 1

        if score >= 3:
            return True
        else:
            return False

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
            extracted_data = parsed_response.get("extracted_data", {})

            analysis_ready_calculated = self._check_analysis_ready(extracted_data)

            # Override LLM's analysis_ready with the data-based calculation
            parsed_response["analysis_ready"] = analysis_ready_calculated
            
            # Set additional fields based on analysis_ready_calculated
            if analysis_ready_calculated:
                parsed_response["conversation_stage"] = "analysis"
                parsed_response["analysis_in_progress"] = False
                parsed_response["analysis_required"] = True
                parsed_response["status"] = "sufficient" # Ensure status is sufficient if ready
                parsed_response["message"] = "정보가 충분합니다. 리스크 분석을 시작합니다." # Update message
                if "follow_up_questions" in parsed_response:
                    del parsed_response["follow_up_questions"] # Remove follow-up questions if analysis is ready
            else:
                # If not ready, ensure these are consistently set for follow-up
                parsed_response["conversation_stage"] = "gathering_info"
                parsed_response["analysis_in_progress"] = True # Still gathering info
                parsed_response["analysis_required"] = False
                
                # Dynamically generate follow-up questions for missing fields
                contract_amount = extracted_data.get("contract_amount")
                penalty_info = extracted_data.get("penalty_info")
                loss_estimate = extracted_data.get("loss_estimate")
                delay_days = extracted_data.get("delay_days")
                delay_risk = extracted_data.get("delay_risk")

                missing_questions = []
                if not contract_amount:
                    missing_questions.append("계약 금액은 얼마입니까?")
                if not penalty_info:
                    missing_questions.append("페널티 조항에 대한 정보가 있습니까?")
                if not loss_estimate:
                    missing_questions.append("예상 손실액은 얼마입니까?")
                if not delay_days and not delay_risk:
                    missing_questions.append("지연 일수 또는 지연 위험에 대한 정보가 있습니까?")
                
                # Update follow_up_questions in parsed_response
                parsed_response["follow_up_questions"] = missing_questions # Always set the missing questions
                parsed_response["message"] = "정보가 불충분합니다." # Generic message
                
                if not missing_questions: # Fallback message if for some reason no questions are generated but analysis is not ready
                    parsed_response["message"] = "아직 정보가 부족합니다. 더 자세한 내용을 알려주시겠습니까?"
                # The LLM's status and message for insufficient info will be kept

            # Mandatory debug print as per instruction (after all calculations, before return)
            print("DEBUG ConversationManager - extracted_data:", json.dumps(extracted_data, ensure_ascii=False))
            print("DEBUG ConversationManager - analysis_ready_calculated:", analysis_ready_calculated)
            
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