from pydantic import BaseModel
from typing import Any, Dict, List, Optional

class AgentResponse(BaseModel):
    response: Any
    agent_type: str
    metadata: Optional[Dict[str, Any]] = {}

class OrchestratorReturn(BaseModel):
    response: AgentResponse
    conversation_history: List[Dict[str, Any]]
    analysis_in_progress: bool