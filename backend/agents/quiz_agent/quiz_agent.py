# backend/agents/quiz_agent/quiz_agent.py

import os
import sys
from typing import Dict, Any, List, Optional
import asyncio # For async graph invocation

# Ensure backend directory is in path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '..', '..', '..'))
sys.path.append(project_root)

# Local imports for the new graph structure
from .state import QuizGraphState
from .graph import quiz_agent_graph

# Compile the graph globally once
compiled_quiz_agent_app = quiz_agent_graph.compile()

class QuizAgent:
    """
    Quiz Agent, now implemented as a thin wrapper around a LangGraph workflow.
    """
    agent_type: str = "quiz"
    
    def __init__(self):
        # The actual components (like LLM, RAG, etc.) are now managed within the graph's nodes.py
        # and initialized globally by QuizAgentComponents.
        pass

    def run(self, 
            user_input: str, 
            conversation_history: List[Dict[str, str]], # Retained for signature consistency
            analysis_in_progress: bool, # Retained for signature consistency
            context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Runs the Quiz Agent's logic by invoking its internal LangGraph.

        Args:
            user_input (str): The user's query or description.
            conversation_history (List[Dict[str, str]]): Conversation history (retained for signature).
            analysis_in_progress (bool): Flag for multi-turn (retained for signature).
            context (Optional[Dict[str, Any]]): Additional context.

        Returns:
            Dict[str, Any]: Output for the orchestrator.
        """
        if context is None:
            context = {}

        # Initialize the state for the quiz agent graph
        initial_state: QuizGraphState = {
            "user_input": user_input,
            "conversation_history": conversation_history, # Pass through
            "analysis_in_progress": analysis_in_progress, # Pass through
            "context": context,
            # Components are initialized globally in nodes.py
            "system_prompt": None, # Will be set by components
            "settings": None,      # Will be set by components
            "llm": None,           # Will be set by components
            # Other fields will be populated by nodes
            "retrieved_documents": None,
            "used_rag": None,
            "rag_context_str": None,
            "llm_messages": None,
            "llm_raw_response_content": None,
            "llm_parsed_response": None,
            "final_response_content": None,
            "llm_output_details": None,
            "final_metadata": None,
            "agent_output_for_orchestrator": None,
        }

        # Invoke the compiled graph
        final_state = asyncio.run(compiled_quiz_agent_app.ainvoke(initial_state))

        # Extract the final output for the orchestrator
        final_output = final_state.get("agent_output_for_orchestrator")
        
        if final_output is None:
            # Fallback for unexpected graph termination
            error_message = "퀴즈 에이전트: 그래프 실행 후 최종 출력을 얻지 못했습니다."
            return {
                "response": {
                    "response": error_message,
                    "agent_type": self.agent_type,
                    "metadata": {"error": error_message}
                },
                "conversation_history": final_state.get("conversation_history", conversation_history),
                "analysis_in_progress": final_state.get("analysis_in_progress", False)
            }
        
        # Ensure the output structure matches what orchestrator expects
        return {
            "response": final_output.get("response", {}),
            "conversation_history": final_state.get("conversation_history", conversation_history),
            "analysis_in_progress": final_state.get("analysis_in_progress", False)
        }
