# backend/agents/riskmanaging/trigger_detector.py

from typing import List
from backend.agents.riskmanaging.config import RISK_AGENT_TRIGGER_WORDS

def detect_risk_trigger(user_input: str) -> bool:
    """
    Detects if the user input contains any of the defined risk managing agent trigger words.

    Args:
        user_input (str): The user's text input.

    Returns:
        bool: True if a trigger word is found, False otherwise.
    """
    user_input_lower = user_input.lower()
    for trigger in RISK_AGENT_TRIGGER_WORDS:
        if trigger.lower() in user_input_lower:
            return True
    return False
