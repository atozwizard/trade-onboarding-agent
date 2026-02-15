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

    # ====== 이메일 코칭 모드 전용 UI ======
    if st.session_state.mode == "email":
        email_mode = st.radio(
            "이메일 모드 선택",
            ["✍️ 작성 (Draft)", "🔍 검토 (Review)"],
            horizontal=True
        )

        if email_mode == "✍️ 작성 (Draft)":
            st.markdown("### 📧 이메일 초안 작성")

            with st.form("email_draft_form"):
                user_input = st.text_area(
                    "요청 사항",
                    placeholder="예: 미국 바이어에게 FOB 조건으로 100개 견적 요청",
                    height=100
                )

                col1, col2 = st.columns(2)
                with col1:
                    recipient_country = st.selectbox(
                        "수신자 국가",
                        ["USA", "Japan", "Korea", "China", "Germany", "UK", "Other"],
                        index=0
                    )
                    relationship = st.selectbox(
                        "관계",
                        ["first_contact", "ongoing", "long_term"],
                        index=0,
                        format_func=lambda x: {
                            "first_contact": "첫 접촉",
                            "ongoing": "진행 중",
                            "long_term": "장기 파트너"
                        }[x]
                    )

                with col2:
                    purpose = st.selectbox(
                        "이메일 목적",
                        ["quotation", "negotiation", "inquiry", "complaint", "follow_up"],
                        index=0,
                        format_func=lambda x: {
                            "quotation": "견적 요청",
                            "negotiation": "협상",
                            "inquiry": "문의",
                            "complaint": "클레임",
                            "follow_up": "후속 조치"
                        }[x]
                    )

                submitted = st.form_submit_button("📧 이메일 초안 생성", use_container_width=True)

                if submitted:
                    if not user_input:
                        st.error("요청 사항을 입력해주세요.")
                    else:
                        with st.spinner("이메일 초안을 생성하는 중..."):
                            response = call_api("email/draft", {
                                "user_input": user_input,
                                "recipient_country": recipient_country,
                                "relationship": relationship,
                                "purpose": purpose
                            })

                            if response:
                                st.success("✅ 이메일 초안이 생성되었습니다!")
                                st.markdown(response.get("response", ""))

                                # 메타데이터 표시
                                with st.expander("📊 생성 정보"):
                                    st.json(response.get("metadata", {}))

        else:  # Review 모드
            st.markdown("### 🔍 이메일 검토")

            with st.form("email_review_form"):
                email_content = st.text_area(
                    "검토할 이메일 내용",
                    placeholder="검토할 이메일 전문을 붙여넣어주세요...",
                    height=200
                )

                col1, col2 = st.columns(2)
                with col1:
                    recipient_country = st.selectbox(
                        "수신자 국가",
                        ["USA", "Japan", "Korea", "China", "Germany", "UK", "Other"],
                        index=0
                    )

                with col2:
                    purpose = st.selectbox(
                        "이메일 목적",
                        ["quotation", "negotiation", "inquiry", "complaint", "follow_up"],
                        index=0,
                        format_func=lambda x: {
                            "quotation": "견적 요청",
                            "negotiation": "협상",
                            "inquiry": "문의",
                            "complaint": "클레임",
                            "follow_up": "후속 조치"
                        }[x]
                    )

                submitted = st.form_submit_button("🔍 이메일 검토", use_container_width=True)

                if submitted:
                    if not email_content:
                        st.error("검토할 이메일 내용을 입력해주세요.")
                    else:
                        with st.spinner("이메일을 검토하는 중..."):
                            response = call_api("email/review", {
                                "email_content": email_content,
                                "recipient_country": recipient_country,
                                "purpose": purpose
                            })

                            if response:
                                st.success("✅ 이메일 검토가 완료되었습니다!")
                                st.markdown(response.get("response", ""))

                                # 메타데이터 표시
                                with st.expander("📊 검토 정보"):
                                    metadata = response.get("metadata", {})
                                    st.json(metadata)

                                    # 리스크 카운트 및 톤 점수 강조 표시
                                    if "risk_count" in metadata:
                                        risk_count = metadata["risk_count"]
                                        if risk_count == 0:
                                            st.success(f"🟢 발견된 리스크: {risk_count}건")
                                        elif risk_count <= 2:
                                            st.warning(f"🟡 발견된 리스크: {risk_count}건")
                                        else:
                                            st.error(f"🔴 발견된 리스크: {risk_count}건")

                                    if "tone_score" in metadata:
                                        tone_score = metadata["tone_score"]
                                        st.metric("톤 점수", f"{tone_score}/10")

    # ====== 일반 채팅 모드 (기존 코드) ======
    else:
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
