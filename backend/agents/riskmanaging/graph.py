# backend/agents/riskmanaging/graph.py
from typing import List, Dict, Optional, Any
from typing import Callable, Literal
from langgraph.graph import StateGraph, END

# Internal imports
from .state import RiskManagingGraphState
from backend.agents.riskmanaging.nodes import (
    prepare_risk_state_node,
    detect_trigger_and_similarity_node,
    assess_conversation_progress_node,
    perform_full_analysis_node,
    format_final_output_node,
    handle_risk_error_node # For error handling path if integrated directly into graph
)

# Define conditional edges decision logic
def decide_next_step(state: RiskManagingGraphState) -> Literal["assess_conversation", "format_output"]:
    # After detect_trigger_and_similarity_node, if analysis is not required, directly format output (e.g., no trigger, early exit).
    if not state.get("analysis_required", False):
        print("---Graph: decide_next_step -> format_output (not analysis_required)---")
        return "format_output"
    # Otherwise, analysis is required, proceed to assess conversation progress
    print("---Graph: decide_next_step -> assess_conversation (analysis_required)---")
    return "assess_conversation"

def decide_after_conversation_assessment(state: RiskManagingGraphState) -> Literal["perform_full_analysis", "format_output"]:
    # After assess_conversation_progress_node, check if analysis is ready.
    if state.get("analysis_ready", False):
        print("---Graph: decide_after_conversation_assessment -> perform_full_analysis (analysis_ready)---")
        return "perform_full_analysis"
    # If not ready, it means we need more info, and the CM would have set the agent_response with follow-up questions.
    print("---Graph: decide_after_conversation_assessment -> format_output (not analysis_ready, need more info)---")
    return "format_output"


# Define the graph
def create_risk_managing_graph() -> StateGraph:
    workflow = StateGraph(RiskManagingGraphState)

    # Define nodes
    workflow.add_node("prepare_state", prepare_risk_state_node)
    workflow.add_node("detect_trigger_and_similarity", detect_trigger_and_similarity_node)
    workflow.add_node("assess_conversation", assess_conversation_progress_node)
    workflow.add_node("perform_full_analysis", perform_full_analysis_node)
    workflow.add_node("format_output", format_final_output_node)
    # Error handling can be added with workflow.add_node("error_handler", handle_risk_error_node)
    # and then workflow.add_edge("error_handler", END) etc.
    # For now, we'll let exceptions propagate to the orchestrator's error handling.

    # Define edges
    workflow.set_entry_point("prepare_state")
    workflow.add_edge("prepare_state", "detect_trigger_and_similarity")
    
    # Conditional routing after trigger/similarity detection
    workflow.add_conditional_edges(
        "detect_trigger_and_similarity",
        decide_next_step,
        {
            "assess_conversation": "assess_conversation",
            "format_output": "format_output" # Passthrough scenario
        }
    )

    # Conditional routing after conversation assessment
    workflow.add_conditional_edges(
        "assess_conversation",
        decide_after_conversation_assessment,
        {
            "perform_full_analysis": "perform_full_analysis",
            "format_output": "format_output" # Follow-up scenario
        }
    )

    workflow.add_edge("perform_full_analysis", "format_output")

    # All paths eventually lead to formatting the final output
    workflow.add_edge("format_output", END)

    return workflow

risk_managing_graph = create_risk_managing_graph()
compiled_risk_managing_app = risk_managing_graph.compile()

class RiskManagingAgent:
    """
    Risk Managing Agent wrapper for the orchestrator.
    Implemented as a thin wrapper around the LangGraph workflow.
    """
    agent_type: str = "riskmanaging"

    def run(self, 
            user_input: str, 
            conversation_history: List[Dict[str, str]], 
            analysis_in_progress: bool, 
            context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if context is None:
            context = {}

        # Initialize the state for the risk managing graph
        initial_state: RiskManagingGraphState = {
            "current_user_input": user_input,
            "conversation_history": conversation_history,
            "analysis_in_progress": analysis_in_progress,
            "risk_trigger_detected": False,
            "risk_similarity_score": 0.0,
            "analysis_required": False,
            "analysis_ready": False,
            "conversation_stage": "initial",
            "extracted_data": {},
            "rag_documents": [],
            "risk_scoring": None,
            "report_generated": None,
            "agent_response": "",
            "error_message": None,
            "user_profile": context.get("user_profile")
        }

        # Invoke the compiled graph
        # Since this is a synchronous run method, we use .invoke()
        final_state = compiled_risk_managing_app.invoke(initial_state)

        # Extract the final agent_response (RiskManagingAgentResponse object)
        agent_response_obj = final_state.get("agent_response")
        
        # If it's a Pydantic object, we might need to dump it
        if hasattr(agent_response_obj, "model_dump"):
            response_payload = agent_response_obj.model_dump()
        else:
            # Fallback
            response_payload = {
                "response": str(agent_response_obj),
                "agent_type": self.agent_type,
                "metadata": {}
            }

        return {
            "response": response_payload,
            "conversation_history": final_state.get("conversation_history", conversation_history),
            "analysis_in_progress": final_state.get("analysis_in_progress", False)
        }


