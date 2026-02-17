from __future__ import annotations

from backend.agents.default_chat.default_chat_agent import DefaultChatAgent


def _run(user_input: str) -> str:
    agent = DefaultChatAgent()
    result = agent.run(
        user_input=user_input,
        conversation_history=[],
        analysis_in_progress=False,
        context={},
    )
    return result["response"]["response"]


def test_default_chat_greeting_response_is_actionable():
    message = _run("안녕")
    assert "무역 실무" in message
    assert "일반적인 답변" not in message


def test_default_chat_weather_response_explains_scope():
    message = _run("내일 서울날씨")
    assert "실시간 날씨 조회" in message
    assert "리스크" in message
    assert "일반적인 답변" not in message


def test_default_chat_generic_fallback_provides_examples():
    message = _run("뭐 할 수 있어?")
    assert "무역/물류 실무" in message
    assert "리스크 분석" in message
    assert "이메일 초안" in message
