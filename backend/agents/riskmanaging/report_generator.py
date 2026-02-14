# backend/agents/riskmanaging/report_generator.py

import json
import uuid # For generating analysis_id
from typing import List, Dict, Any, Optional
import openai
from openai import OpenAI
from langsmith import traceable
import os

from backend.config import get_settings
from backend.agents.riskmanaging.prompt_loader import (
    REPORT_GENERATION_PROMPT,
    INPUT_SUMMARY_PROMPT,
    LOSS_SIMULATION_QUALITATIVE_PROMPT,
    CONTROL_GAP_ANALYSIS_PROMPT,
    PREVENTION_STRATEGY_PROMPT,
    CONFIDENCE_SCORE_PROMPT,
    RISK_AGENT_SYSTEM_PROMPT # To ensure persona is always consistent
)
from backend.agents.riskmanaging.schemas import (
    RiskManagingAgentInput,
    RiskReport,
    RiskScoring,
    LossSimulation,
    ControlGapAnalysis,
    PreventionStrategy,
    RiskFactor, # Added
    ReportRiskFactor # Added
)
from backend.agents.riskmanaging.config import AGENT_PERSONA # For persona context

class ReportGenerator:
    def __init__(self):
        self.settings = get_settings()
        if not self.settings.upstage_api_key:
            print("Warning: UPSTAGE_API_KEY is not set. LLM calls for ReportGenerator will fail.")
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

    @traceable(name="report_generator_generate")
    def generate_report(
        self,
        agent_input: RiskManagingAgentInput,
        risk_scoring: RiskScoring,
        similar_cases: List[Dict[str, Any]],
        evidence_sources: List[str],
        rag_documents: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None
    ) -> RiskReport:
        """
        Generates the final Risk Report in JSON format.
        """
        if not self.llm:
            raise Exception("LLM client not initialized for ReportGenerator due to missing API key.")

        try:
            # 1. Generate input_summary
            input_summary = self._generate_input_summary(agent_input)

            # 2. Generate loss_simulation (qualitative part)
            loss_simulation_qualitative = self._generate_loss_simulation_qualitative(risk_scoring)
            loss_simulation = LossSimulation(
                quantitative=None, # For now, quantitative is None, could be added later
                qualitative=loss_simulation_qualitative
            )

            # 3. Generate control_gap_analysis
            control_gap_analysis = self._generate_control_gap_analysis(risk_scoring)

            # 4. Generate prevention_strategy
            prevention_strategy = self._generate_prevention_strategy(risk_scoring, control_gap_analysis)

            # 5. Generate confidence_score
            confidence_score = self._generate_confidence_score(risk_scoring, rag_documents)

            # Consolidate risk factors into a dictionary of ReportRiskFactor objects for frontend display
            risk_factors_dict = {}
            for rf in risk_scoring.risk_factors:
                key = rf.name # Use rf.name as the key for the dictionary
                risk_factors_dict[key] = ReportRiskFactor(
                    name_kr=rf.name, # Use rf.name as name_kr
                    impact=rf.impact,
                    likelihood=rf.likelihood,
                    score=rf.risk_score # Map rf.risk_score to score
                )

            # Construct the final report data structure
            final_report_model = RiskReport(
                analysis_id=str(uuid.uuid4()), # Generate new ID here
                input_summary=input_summary,
                risk_factors=risk_factors_dict, # Pass the dictionary of ReportRiskFactor here
                risk_scoring=risk_scoring,
                loss_simulation=loss_simulation,
                control_gap_analysis=control_gap_analysis,
                prevention_strategy=prevention_strategy,
                similar_cases=similar_cases,
                confidence_score=confidence_score,
                evidence_sources=evidence_sources
            )
            return final_report_model

        except Exception as e:
            print(f"An unexpected error occurred in ReportGenerator: {e}")
            raise Exception(f"보고서 생성 중 예상치 못한 오류 발생: {e}")

    def _generate_input_summary(self, agent_input: RiskManagingAgentInput) -> str:
        messages = [
            {"role": "system", "content": RISK_AGENT_SYSTEM_PROMPT},
            {"role": "user", "content": INPUT_SUMMARY_PROMPT.format(
                user_input=agent_input.user_input,
                conversation_history=json.dumps(agent_input.conversation_history, ensure_ascii=False) if agent_input.conversation_history else "없음"
            )}
        ]
        response = self.llm.chat.completions.create(model="solar-pro2", messages=messages, temperature=0.1).choices[0].message.content
        return response

    def _generate_loss_simulation_qualitative(self, risk_scoring: RiskScoring) -> str:
        messages = [
            {"role": "system", "content": RISK_AGENT_SYSTEM_PROMPT},
            {"role": "user", "content": LOSS_SIMULATION_QUALITATIVE_PROMPT.format(
                risk_summary=risk_scoring.overall_assessment
            )}
        ]
        response = self.llm.chat.completions.create(model="solar-pro2", messages=messages, temperature=0.2).choices[0].message.content
        return response

    def _generate_control_gap_analysis(self, risk_scoring: RiskScoring) -> ControlGapAnalysis:
        messages = [
            {"role": "system", "content": RISK_AGENT_SYSTEM_PROMPT},
            {"role": "user", "content": CONTROL_GAP_ANALYSIS_PROMPT.format(
                risk_summary=risk_scoring.overall_assessment
            )}
        ]
        response_content = self.llm.chat.completions.create(
            model="solar-pro2", messages=messages, temperature=0.2, response_format={"type": "json_object"}
        ).choices[0].message.content
        return ControlGapAnalysis(**json.loads(response_content))

    def _generate_prevention_strategy(self, risk_scoring: RiskScoring, control_gap_analysis: ControlGapAnalysis) -> PreventionStrategy:
        messages = [
            {"role": "system", "content": RISK_AGENT_SYSTEM_PROMPT},
            {"role": "user", "content": PREVENTION_STRATEGY_PROMPT.format(
                risk_summary=risk_scoring.overall_assessment,
                control_gaps_json=control_gap_analysis.model_dump_json(indent=2, exclude_none=True)
            )}
        ]
        response_content = self.llm.chat.completions.create(
            model="solar-pro2", messages=messages, temperature=0.2, response_format={"type": "json_object"}
        ).choices[0].message.content
        return PreventionStrategy(**json.loads(response_content))

    def _generate_confidence_score(self, risk_scoring: RiskScoring, rag_documents: List[Dict[str, Any]]) -> float:
        messages = [
            {"role": "system", "content": RISK_AGENT_SYSTEM_PROMPT},
            {"role": "user", "content": CONFIDENCE_SCORE_PROMPT.format(
                risk_report_json=risk_scoring.model_dump_json(indent=2, exclude_none=True),
                rag_documents=json.dumps(rag_documents, indent=2, ensure_ascii=False)
            )}
        ]
        response_content = self.llm.chat.completions.create(model="solar-pro2", messages=messages, temperature=0.1).choices[0].message.content
        try:
            return float(response_content.strip())
        except ValueError:
            print(f"Warning: Could not parse confidence score from LLM response: {response_content}. Defaulting to 0.5.")
            return 0.5

# Example Usage (for testing)
if __name__ == '__main__':
    settings = get_settings()
    if not settings.upstage_api_key:
        print("UPSTAGE_API_KEY is not set. ReportGenerator will not function properly.")
        exit()

    generator = ReportGenerator()
    
    # Mock data for testing
    mock_agent_input = RiskManagingAgentInput(
        user_input="해외 공급업체 선적 지연으로 클레임 발생 위험. 생산 라인 중단 가능성.",
        conversation_history=[
            {"role": "User", "content": "해외 공급업체로부터 선적이 3일 지연될 것 같다는 통보를 받았습니다."},
            {"role": "Agent", "content": "어떤 계약 건인지, 페널티 조항은 있는지, 그리고 지연으로 인해 예상되는 구체적인 영향이 무엇인지 알려주십시오."},
            {"role": "User", "content": "A사와의 10만 달러 규모 계약이고, 5일 이상 지연 시 일당 1%의 페널티가 있습니다. 저희 생산 라인도 멈출 수 있습니다."}
        ]
    )

    mock_risk_scoring = RiskScoring(
        overall_risk_level="high",
        risk_factors=[
            RiskFactor(
                name="재정적 손실", impact=4, likelihood=4, risk_score=16, risk_level="critical",
                reasoning="생산 라인 중단으로 인한 기회비용 및 5일 이상 지연 시 페널티 발생",
                mitigation_suggestions=["계약서 검토", "대체 운송 수단 확보"]
            ),
            RiskFactor(
                name="일정 지연", impact=5, likelihood=4, risk_score=20, risk_level="critical",
                reasoning="3일 지연 통보, 생산 라인 중단 가능성으로 추가 지연 우려",
                mitigation_suggestions=["공급업체와 긴급 협상", "내부 일정 재조정"]
            )
        ],
        overall_assessment="해외 공급업체 선적 지연으로 재정적 손실 및 생산 일정에 심각한 리스크가 예상됩니다."
    )
    
    mock_similar_cases = [
        {"content": "2023년 B사 선적 지연 사례: 생산 라인 5일 중단, 5만 달러 손실 발생", "source": "claims.json", "topic": ["delay", "claim"]},
        {"content": "해외 계약 지연 페널티 적용 가이드라인", "source": "country_rules.json", "topic": ["penalty", "contract"]}
    ]
    mock_evidence_sources = ["claims.json", "country_rules.json"]
    mock_rag_documents = [
        {"document": "국가별 운송 지연 페널티 규정: 5일 초과 시 일당 1% 페널티 부과.", "metadata": {"source_dataset": "country_rules.json", "topic": ["shipping", "penalty"]}},
        {"document": "선적 지연 발생 시 고객사 대응 매뉴얼: 즉시 통보 및 대안 모색.", "metadata": {"source_dataset": "internal_process.json", "topic": ["delay", "response"]}}
    ]

    print("\n--- Report Generator Test ---") # Corrected string literal
    try:
        report = generator.generate_report(
            agent_input=mock_agent_input,
            risk_scoring=mock_risk_scoring,
            similar_cases=mock_similar_cases,
            evidence_sources=mock_evidence_sources,
            rag_documents=mock_rag_documents
        )
        print(json.dumps(report.model_dump(), indent=2, ensure_ascii=False))
        print("\nReport Generator test passed!")
    except Exception as e:
        print(f"Report Generator test failed: {e}")