from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple


class DefaultChatAgent:
    """
    Lightweight fallback agent for non-domain or small-talk inputs.
    It avoids generic template text and provides actionable next steps.
    """

    agent_type: str = "default_chat"

    _GREETING_RE = re.compile(r"(안녕|하이|hello|hi|반가워)", re.IGNORECASE)
    _THANKS_RE = re.compile(r"(고마워|감사|thanks|thx)", re.IGNORECASE)
    _WEATHER_RE = re.compile(r"(날씨|weather)", re.IGNORECASE)

    def _build_response(
        self,
        user_input: str,
        _conversation_history: List[Dict[str, str]],
        _context: Dict[str, Any],
    ) -> Tuple[str, str]:
        message = (user_input or "").strip()
        normalized = message.lower()

        if self._GREETING_RE.search(normalized):
            return (
                "안녕하세요. 무역 실무 기준으로 바로 도와드릴 수 있습니다.\n"
                "- 리스크 분석: `선적 지연으로 패널티가 걱정돼요`\n"
                "- 이메일 초안/리뷰: `이메일 초안 영어로 작성해줘` / `이 메일 리뷰해줘`\n"
                "- 무역 퀴즈: `무역용어 퀴즈 내줘`",
                "greeting",
            )

        if self._THANKS_RE.search(normalized):
            return (
                "확인했습니다. 다음 작업이 필요하면 바로 이어서 지시해 주세요.\n"
                "예: `리스크 분석 계속`, `이메일 톤 더 공식적으로 수정`, `퀴즈 한 문제 더`",
                "thanks",
            )

        if self._WEATHER_RE.search(normalized):
            return (
                "현재 이 에이전트는 실시간 날씨 조회 기능은 제공하지 않습니다.\n"
                "대신 무역 실무 기준으로는 `기상 이슈가 선적 일정/패널티에 미치는 리스크` 분석을 바로 진행할 수 있습니다.",
                "out_of_scope_weather",
            )

        return (
            "요청을 확인했습니다. 이 시스템은 무역/물류 실무 작업에 최적화되어 있습니다.\n"
            "원하는 작업을 아래 형식으로 입력해 주세요:\n"
            "- `리스크 분석: [상황 설명]`\n"
            "- `이메일 초안: [목적/수신자/핵심조건]`\n"
            "- `이메일 리뷰: [이메일 본문]`\n"
            "- `무역 퀴즈: [주제]`",
            "fallback",
        )

    def run(
        self,
        user_input: str,
        conversation_history: List[Dict[str, str]],
        analysis_in_progress: bool,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        updated_history = list(conversation_history)
        updated_history.append({"role": "User", "content": user_input})

        response_message, mode = self._build_response(
            user_input=user_input,
            _conversation_history=conversation_history,
            _context=context or {},
        )
        updated_history.append({"role": "Agent", "content": response_message})

        return {
            "response": {
                "response": response_message,
                "agent_type": self.agent_type,
                "metadata": {"fallback_mode": mode},
            },
            "conversation_history": updated_history,
            "analysis_in_progress": False,
        }
