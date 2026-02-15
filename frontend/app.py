"""
Streamlit Frontend - Trade Onboarding AI Coach
"""
import streamlit as st
import requests
from typing import Dict, Any

# API 설정
API_BASE_URL = "http://localhost:8000/api"

# 페이지 설정
st.set_page_config(
    page_title="물류·무역 온보딩 AI 코치",
    page_icon="📦",
    layout="wide"
)

# 세션 상태 초기화
if "messages" not in st.session_state:
    st.session_state.messages = []

if "mode" not in st.session_state:
    st.session_state.mode = "chat"


def call_api(endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Call backend API"""
    try:
        response = requests.post(f"{API_BASE_URL}/{endpoint}", json=data)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"API 호출 오류: {str(e)}")
        return None


def main():
    """Main application"""

    # 사이드바
    with st.sidebar:
        st.title("📦 물류·무역 AI 코치")
        st.markdown("---")

        # 모드 선택
        mode = st.radio(
            "기능 선택",
            ["💬 자유 채팅", "📝 퀴즈 학습", "📧 이메일 코칭", "⚠️ 실수 예측", "👔 대표 보고 연습"],
            key="mode_selector"
        )

        # 모드별 설정
        mode_map = {
            "💬 자유 채팅": "chat",
            "📝 퀴즈 학습": "quiz",
            "📧 이메일 코칭": "email",
            "⚠️ 실수 예측": "mistake",
            "👔 대표 보고 연습": "ceo"
        }
        st.session_state.mode = mode_map[mode]

        st.markdown("---")

        # 대화 초기화 버튼
        if st.button("🗑️ 대화 초기화"):
            st.session_state.messages = []
            st.rerun()

        st.markdown("---")
        st.markdown("### 📊 통계")
        st.metric("총 대화 수", len(st.session_state.messages))

    # 메인 영역
    st.title("물류·무역 온보딩 AI 코치")

    # 모드별 설명
    mode_descriptions = {
        "chat": "자유롭게 질문해주세요. AI가 적절한 기능으로 안내해드립니다.",
        "quiz": "무역 실무 퀴즈를 풀어보세요.",
        "email": "무역 이메일 작성을 도와드립니다.",
        "mistake": "업무 실수를 예측하고 예방법을 제시합니다.",
        "ceo": "대표 보고 상황을 시뮬레이션합니다."
    }

    st.info(mode_descriptions[st.session_state.mode])

    # 채팅 히스토리 표시
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # 사용자 입력
    if prompt := st.chat_input("메시지를 입력하세요..."):
        # 사용자 메시지 추가
        st.session_state.messages.append({"role": "user", "content": prompt})

        with st.chat_message("user"):
            st.markdown(prompt)

        # AI 응답
        with st.chat_message("assistant"):
            with st.spinner("생각하는 중..."):
                # API 호출
                response = call_api("chat", {
                    "message": prompt,
                    "context": {
                        "mode": st.session_state.mode
                    }
                })

                if response:
                    ai_message = response.get("response", "응답을 받지 못했습니다.")
                    st.markdown(ai_message)

                    # AI 메시지 추가
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": ai_message
                    })
                else:
                    st.error("서버와 통신할 수 없습니다. 백엔드 서버가 실행 중인지 확인해주세요.")


if __name__ == "__main__":
    main()
