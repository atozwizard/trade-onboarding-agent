import asyncio
import os
import sys
import json # Import json for printing

# Add project root to sys.path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__)))
sys.path.append(project_root)

# Import necessary components from the refactored agent
from backend.agents.riskmanaging.graph import compiled_risk_managing_app
from backend.agents.riskmanaging.state import RiskManagingAgentInput  # Fixed: import from state.py
from backend.agents.riskmanaging.state import RiskManagingGraphState

# Load environment variables if not already set (e.g., from .env file)
from dotenv import load_dotenv
load_dotenv()

async def run_risk_managing_agent_test():
    print("--- Starting Risk Managing Agent Test ---")
    print("Test Scenario: Full Risk Analysis with Comprehensive Information\n")
    
    # Test input with comprehensive information to trigger full analysis
    test_user_input = """
    중국 거래처와의 대규모 선적 건에서 심각한 문제가 발생했습니다.
    
    상황:
    - 계약 금액: 50만 달러
    - 선적 예정일: 2주 전 (이미 2주 지연)
    - 페널티 조항: 하루당 계약금의 0.5% (일 2,500달러)
    - 현재까지 예상 손실: 약 35,000달러
    - 고객사에서 계약 해지 경고 발송
    
    원인:
    - 공급업체의 원자재 수급 문제
    - HS Code 분류 오류로 통관 지연
    - 내부 커뮤니케이션 부재로 문제 인지 지연
    
    이 상황에 대한 리스크 분석과 대응 방안이 필요합니다.
    """
    
    test_conversation_history = []
    
    # The actual agent_input structure for the graph's entry point
    # Note: the prepare_risk_state_node expects agent_input: RiskManagingAgentInput
    agent_input_data = {
        "user_input": test_user_input,
        "conversation_history": test_conversation_history,
        "context": {},
    }
    
    # The initial state passed to the graph
    # Prepare initial state matching RiskManagingGraphState
    initial_state: RiskManagingGraphState = {
        "current_user_input": test_user_input,  # Use the test input
        "conversation_history": test_conversation_history,  # Use the test history
        "risk_trigger_detected": False,
        "risk_similarity_score": 0.0,
        "analysis_required": False,
        "analysis_ready": False,
        "analysis_in_progress": False,
        "conversation_stage": "initial",
        "extracted_data": {},
        "rag_documents": [],
        "risk_scoring": None,
        "report_generated": None,
        "agent_response": "",
        "error_message": None
    }

    # Invoke the compiled graph
    print("\n--- Invoking compiled_risk_managing_app ---")
    print(f"DEBUG: initial_state['current_user_input'] = '{initial_state['current_user_input']}'")
    try:
        result = compiled_risk_managing_app.invoke(initial_state)

        # Display results
        print("\n--- Test Execution Result ---")
        print(f"Agent Response:\n{result.get('agent_response', 'No response')}")
        print(f"\nRisk Trigger Detected: {result.get('risk_trigger_detected', False)}")
        print(f"Similarity Score: {result.get('risk_similarity_score', 0.0):.4f}")
        print(f"Analysis Required: {result.get('analysis_required', False)}")
        print(f"Conversation Stage: {result.get('conversation_stage', 'unknown')}")
        
        if result.get('report_generated'):
            print("\n--- Risk Report Generated ---")
            print(result['report_generated'])

    except KeyError as e:
        print(f"\n--- An ERROR occurred during test execution ---")
        print(f"Error: {e}")
        print("Please ensure your UPSTAGE_API_KEY is correctly set in your .env file")
        print("and that all required state fields are properly initialized.")
    except Exception as e:
        print(f"\n--- An ERROR occurred during test execution ---")
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        print("Please ensure your UPSTAGE_API_KEY is correctly set in your .env file or environment variables.")

if __name__ == "__main__":
    asyncio.run(run_risk_managing_agent_test())
