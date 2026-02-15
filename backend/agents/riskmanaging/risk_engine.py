# backend/agents/riskmanaging/risk_engine.py

import json
from typing import List, Dict, Any, Optional
import openai
from openai import OpenAI
from langsmith import traceable
import os

from backend.config import get_settings
from backend.agents.riskmanaging.prompt_loader import RISK_ENGINE_EVALUATION_PROMPT, RISK_AGENT_SYSTEM_PROMPT
from backend.agents.riskmanaging.schemas import RiskManagingAgentInput, RiskScoring, RiskFactor
from backend.agents.riskmanaging.config import RISK_EVALUATION_ITEMS, RISK_LEVEL_THRESHOLDS, AGENT_PERSONA

class RiskEngine:
    def __init__(self):
        self.settings = get_settings()
        if not self.settings.upstage_api_key:
            print("Warning: UPSTAGE_API_KEY is not set. LLM calls for RiskEngine will fail.")
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

    @traceable(name="risk_engine_evaluate")
    def evaluate_risk(self, agent_input: RiskManagingAgentInput, rag_documents: List[Dict[str, Any]]) -> RiskScoring:
        """
        Evaluates various risk factors based on user input, conversation history, and RAG documents.

        Args:
            agent_input (RiskManagingAgentInput): The current user input and conversation history.
            rag_documents (List[Dict[str, Any]]): Documents retrieved from RAG.

        Returns:
            RiskScoring: A Pydantic model containing the overall risk assessment.
        """
        if not self.llm:
            raise Exception("LLM client not initialized for RiskEngine due to missing API key.")

        risk_evaluation_items_json = json.dumps([
            {"name": item["name"], "description": item["description"]}
            for key, item in RISK_EVALUATION_ITEMS.items()
        ], ensure_ascii=False, indent=2)

        conversation_history_str = ""
        if agent_input.conversation_history:
            for turn in agent_input.conversation_history:
                conversation_history_str += f"{turn.get('role', 'User')}: {turn.get('content', '')}\n" # Corrected line
        
        rag_documents_str = ""
        if rag_documents:
            for i, doc in enumerate(rag_documents):
                rag_documents_str += f"""문서 {i+1} (출처: {doc['metadata'].get('source_dataset', 'unknown')} | 주제: {', '.join(doc['metadata'].get('topic', []))}):
{doc['document']}

"""
        
        # Prepare messages for the LLM
        messages = [
            {"role": "system", "content": RISK_AGENT_SYSTEM_PROMPT}, # Use the overall agent system prompt
            {"role": "user", "content": RISK_ENGINE_EVALUATION_PROMPT.format(
                risk_evaluation_items_json=risk_evaluation_items_json,
                user_input=agent_input.user_input,
                conversation_history=conversation_history_str if conversation_history_str else "없음",
                rag_documents=rag_documents_str if rag_documents_str else "없음"
            )}
        ]

        try:
            chat_completion = self.llm.chat.completions.create(
                model="solar-pro2",
                messages=messages,
                temperature=0.2,
                response_format={"type": "json_object"}
            )
            llm_response_content = chat_completion.choices[0].message.content
            
            # Parse the LLM's JSON response into RiskScoring
            risk_scoring_data = json.loads(llm_response_content)
            
            # Dynamically calculate risk_score and risk_level if LLM doesn't provide it
            # Or validate if LLM provided it correctly
            for factor in risk_scoring_data.get("risk_factors", []):
                impact = factor.get("impact", 0)
                likelihood = factor.get("likelihood", 0)
                factor["risk_score"] = impact * likelihood
                factor["risk_level"] = self._get_risk_level(factor["risk_score"])
            
            risk_scoring = RiskScoring(**risk_scoring_data)
            return risk_scoring

        except openai.APIError as e:
            print(f"Upstage API Error during risk evaluation: {e}")
            raise Exception(f"LLM API 호출 중 오류가 발생했습니다: {e}")
        except json.JSONDecodeError as e:
            print(f"Failed to parse LLM response as JSON in RiskEngine: {llm_response_content[:500]}... Error: {e}")
            raise Exception(f"LLM 응답 파싱 오류: {e}")
        except Exception as e:
            print(f"An unexpected error occurred in RiskEngine: {e}")
            raise Exception(f"리스크 평가 중 예상치 못한 오류 발생: {e}")

    def _get_risk_level(self, risk_score: int) -> str:
        """Determines the risk level based on the risk score."""
        if risk_score >= RISK_LEVEL_THRESHOLDS["critical"]:
            return "critical"
        elif risk_score >= RISK_LEVEL_THRESHOLDS["high"]:
            return "high"
        elif risk_score >= RISK_LEVEL_THRESHOLDS["medium"]:
            return "medium"
        else:
            return "low"

# Example Usage (for testing)
if __name__ == '__main__':
    settings = get_settings()
    if not settings.upstage_api_key:
        print("UPSTAGE_API_KEY is not set. RiskEngine will not function properly.")
        exit()

    engine = RiskEngine()
    
    test_input = RiskManagingAgentInput(
        user_input="해외 공급업체로부터 선적이 3일 지연될 것 같다는 통보를 받았습니다. 계약 위반인가요?",
        conversation_history=[
            {"role": "User", "content": "해외 공급업체로부터 선적이 3일 지연될 것 같다는 통보를 받았습니다."},
            {"role": "Agent", "content": "어떤 계약 건인지, 페널티 조항은 있는지, 그리고 지연으로 인해 예상되는 구체적인 영향이 무엇인지 알려주십시오."},
            {"role": "User", "content": "A사와의 10만 달러 규모 계약이고, 5일 이상 지연 시 일당 1%의 페널티가 있습니다. 저희 생산 라인도 멈출 수 있습니다."}
        ]
    )
    
    test_rag_docs = [
        {"document": "국가별 운송 지연 페널티 규정: 5일 초과 시 일당 1% 페널티 부과.", "metadata": {"source_dataset": "country_rules.json", "topic": ["shipping", "penalty"]}},
        {"document": "선적 지연 발생 시 고객사 대응 매뉴얼: 즉시 통보 및 대안 모색.", "metadata": {"source_dataset": "internal_process.json", "topic": ["delay", "response"]}}
    ]

    print("\n--- Risk Engine Test ---")
    try:
        risk_scoring = engine.evaluate_risk(test_input, test_rag_docs)
        print(json.dumps(risk_scoring.model_dump(), indent=2, ensure_ascii=False))
        print("\nRisk Engine test passed!")
    except Exception as e:
        print(f"Risk Engine test failed: {e}")