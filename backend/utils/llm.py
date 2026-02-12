"""
공통 LLM 호출 유틸리티
- Upstage Solar LLM 인스턴스 생성 및 공통 호출 함수 제공
"""
from functools import lru_cache

from langchain_upstage import ChatUpstage
from langchain_core.messages import HumanMessage, SystemMessage

from backend.config import get_settings


@lru_cache()
def get_llm(model: str = "solar-pro", temperature: float = 0.7) -> ChatUpstage:
    """캐싱된 LLM 인스턴스를 반환합니다."""
    settings = get_settings()
    return ChatUpstage(
        api_key=settings.upstage_api_key,
        model=model,
        temperature=temperature,
    )


async def call_llm(
    user_message: str,
    system_prompt: str = "",
    model: str = "solar-pro",
    temperature: float = 0.7,
) -> str:
    """LLM을 호출하고 응답 텍스트를 반환합니다.

    Args:
        user_message: 사용자 메시지
        system_prompt: 시스템 프롬프트 (선택)
        model: 모델명 (기본: solar-pro)
        temperature: 온도 (기본: 0.7)

    Returns:
        LLM 응답 텍스트
    """
    llm = get_llm(model=model, temperature=temperature)

    messages = []
    if system_prompt:
        messages.append(SystemMessage(content=system_prompt))
    messages.append(HumanMessage(content=user_message))

    response = await llm.ainvoke(messages)
    return response.content
