from typing import Dict, Any, List, Optional

class DefaultChatAgent:
    """A simple agent for general conversation or fallback."""
    agent_type: str = "default_chat"
    def run(self, user_input: str, conversation_history: List[Dict[str, str]], analysis_in_progress: bool, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        updated_history = list(conversation_history)
        updated_history.append({"role": "User", "content": user_input})
        
        response_message = f"'{user_input}' 에 대한 일반적인 답변입니다. 다른 도움이 필요하신가요?"
        updated_history.append({"role": "Agent", "content": response_message})

        return {
            "response": {
                "response": response_message,
                "agent_type": self.agent_type,
                "metadata": {}
            },
            "conversation_history": updated_history,
            "analysis_in_progress": False
        }
