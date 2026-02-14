import streamlit as st
import requests
import json
import uuid # Import for UUID generation
from typing import Dict, Any, List, Optional
import time

# API 설정
API_BASE_URL = "http://localhost:8000/api"

# Define risk level color map based on config.py (Korean names for display)
RISK_COLOR_MAP = {
    "critical": "#D32F2F",  # 진한 빨강
    "high": "#F57C00",      # 주황
    "medium": "#FBC02D",    # 노랑
    "low": "#1976D2",       # 파랑
    "passthrough": "#388E3C" # 초록 (for general info, not a risk per se)
}

# Persona configuration from backend for consistent tone
# Replicating here for frontend display consistency, though backend drives actual responses
AGENT_PERSONA = {
    "tone": "담백하고 직설적",
    "emotional_expression": "금지",
    "exaggeration": "금지",
    "feedback_style": "실제 회사 상사 피드백 톤 유지",
    "judgment_criteria": [
        "회사 기준",
        "실무 기준",
        "실제 발생 가능한 리스크",
        "내부 보고 기준",
    ],
    "response_style": "친절한 설명형이 아니라 실무 피드백 형식",
    "always_include": [
        "무엇이 문제인지",
        "왜 문제인지",
        "실제 발생 가능한 상황",
        "지금 해야 할 행동",
    ],
    "never_include": [
        "과도한 공감",
        "감정 위로",
        "불필요한 장문 설명",
        "추상적 조언",
    ],
}


# 페이지 설정
st.set_page_config(
    page_title="기업 리스크 관리 AI",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for executive dashboard feel and conversation clarity
st.markdown("""
<style>
    /* General Styling */
    .reportview-container {
        background: #f0f2f6;
    }
    .main .block-container {
        padding-top: 2rem;
        padding-right: 2rem;
        padding-left: 2rem;
        padding-bottom: 2rem;
    }
    h1, h2, h3, h4, h5, h6 {
        color: #262730;
    }
    .stButton > button {
        background-color: #4CAF50;
        color: white;
        border-radius: 5px;
        border: none;
        padding: 10px 20px;
        font-size: 16px;
        cursor: pointer;
    }
    .stButton > button:hover {
        background-color: #45a049;
    }

    /* Chat message styling for clarity */
    .chat-container {
        display: flex;
        flex-direction: column;
        gap: 15px;
        margin-top: 20px;
    }
    .chat-message {
        padding: 10px 15px;
        border-radius: 10px;
        max-width: 70%;
        position: relative;
        font-size: 1rem;
        line-height: 1.5;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
    }
    .user-message {
        background-color: #e0f2f1; /* Light teal for user */
        align-self: flex-end;
        margin-left: auto;
        color: #262730;
        border-bottom-right-radius: 2px;
    }
    .ai-message {
        background-color: #ffffff; /* White for AI */
        align-self: flex-start;
        margin-right: auto;
        color: #262730;
        border-bottom-left-radius: 2px;
    }
    .message-role {
        font-weight: bold;
        margin-bottom: 5px;
        display: flex;
        align-items: center;
        gap: 5px;
    }
    .user-icon {
        color: #00796B; /* Darker teal */
    }
    .ai-icon {
        color: #3F51B5; /* Indigo */
    }

    /* Risk Report Styling */
    .risk-report-container {
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        padding: 20px;
        margin-top: 20px;
        box-shadow: 0 4px 10px rgba(0,0,0,0.08);
        background-color: #fcfcfc;
    }
    .risk-level-display {
        padding: 8px 15px;
        border-radius: 5px;
        font-weight: bold;
        color: white;
        text-align: center;
        margin-bottom: 15px;
        font-size: 1.1em;
    }
    .risk-factor-item {
        margin-bottom: 10px;
        padding-left: 10px;
        border-left: 3px solid #ccc;
    }
    .stMetric {
        background-color: #f8f8f8;
        padding: 15px;
        border-radius: 8px;
        border: 1px solid #eee;
        margin-bottom: 15px;
    }
    .stProgress > div > div > div > div {
        background-color: #3F51B5; /* Primary color for progress bars */
    }
    
    /* Agent Thinking Indicator */
    .stSpinner > div > div {
        border-top-color: #3F51B5; /* Match primary color */
    }
    .stSpinner > div > div > div {
        color: #3F51B5;
    }

</style>
""", unsafe_allow_html=True)


# 세션 상태 초기화
if "messages" not in st.session_state:
    st.session_state.messages = []
    
if "risk_analysis_history" not in st.session_state:
    st.session_state.risk_analysis_history = []

if "session_id" not in st.session_state: # Initialize session_id
    st.session_state.session_id = str(uuid.uuid4())


def call_api(endpoint: str, session_id: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Call backend API"""
    try:
        # Add session_id to the data payload
        data["session_id"] = session_id
        response = requests.post(f"{API_BASE_URL}/{endpoint}", json=data)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"백엔드 API 호출 오류: {e}")
        return None
    except json.JSONDecodeError:
        st.error(f"API 응답 디코딩 오류: 유효하지 않은 JSON 응답입니다. {response.text}")
        return None
    except Exception as e:
        st.error(f"예상치 못한 오류 발생: {e}")
        return None


def display_message(role: str, content: str):
    """Custom function to display chat messages with icons and styling."""
    if role == "user":
        st.markdown(
            f"""
            <div class="chat-message user-message">
                <div class="message-role"><span class="user-icon">👤</span> 사용자</div>
                {content}
            </div>
            """,
            unsafe_allow_html=True
        )
    else: # role == "assistant"
        st.markdown(
            f"""
            <div class="chat-message ai-message">
                <div class="message-role"><span class="ai-icon">🤖</span> AI 비서</div>
                {content}
            </div>
            """,
            unsafe_allow_html=True
        )

def display_risk_report(report_data: Dict[str, Any]):
    """
    Displays a structured and visually appealing risk report.
    Applies color coding based on risk level.
    """
    analysis_id = report_data.get("analysis_id", "N/A")
    overall_risk_level = report_data.get("risk_scoring", {}).get("overall_risk_level", "Unknown")
    overall_risk_score = report_data.get("risk_scoring", {}).get("overall_risk_score", 0)
    risk_factors = report_data.get("risk_scoring", {}).get("risk_factors", {})
    response_summary = report_data.get("response_summary", "요약 없음")
    suggested_actions = report_data.get("suggested_actions", [])
    similar_cases = report_data.get("similar_cases", [])
    evidence_sources = report_data.get("evidence_sources", [])

    # Get color for overall risk level
    risk_color = RISK_COLOR_MAP.get(overall_risk_level.lower(), "#607D8B") # Default grey

    st.markdown(f"""
    <div class="risk-report-container">
        <h3>🛡️ 리스크 분석 보고서 <small>(ID: {analysis_id[:8]})</small></h3>
        <div style="background-color: {risk_color};" class="risk-level-display">
            종합 리스크 레벨: {overall_risk_level} (점수: {overall_risk_score:.1f})
        </div>
    """, unsafe_allow_html=True)

    st.subheader("📊 리스크 요약")
    st.write(response_summary)

    st.subheader("⚠️ 주요 리스크 요인 분석")
    if risk_factors:
        for factor_name, factor_data in risk_factors.items():
            name_kr = factor_data.get("name_kr", factor_name)
            impact = factor_data.get("impact", 0)
            likelihood = factor_data.get("likelihood", 0)
            score = factor_data.get("score", 0)
            description = factor_data.get("description", "")
            reason = factor_data.get("reason", "")

            st.markdown(f"**{name_kr}** (영향: {impact}, 발생 가능성: {likelihood}, 점수: {score:.1f})")
            st.caption(description)
            with st.expander("상세 분석 및 근거"):
                st.write(reason)
            st.progress(min(score / 25.0, 1.0)) # Assuming max score is 5*5=25

    st.subheader("✅ 제안하는 조치")
    if suggested_actions:
        for action in suggested_actions:
            st.markdown(f"- {action}")
    else:
        st.info("현재 상황에 대한 제안 조치가 없습니다.")

    st.subheader("🔍 유사 사례 및 근거 자료")
    if similar_cases or evidence_sources:
        if similar_cases:
            st.markdown("**유사 사례:**")
            for case in similar_cases:
                st.markdown(f"- {case}")
        if evidence_sources:
            st.markdown("**근거 자료:**")
            for source in evidence_sources:
                st.markdown(f"- {source}")
    else:
        st.info("관련 유사 사례 또는 근거 자료를 찾을 수 없습니다.")

    st.markdown("</div>", unsafe_allow_html=True)


def main():
    """Main application"""

    # --- Sidebar ---
    with st.sidebar:
        st.title("🛡️ 기업 리스크 관리 AI")
        st.markdown("---")
        
        # New Analysis / Clear Conversation Button for risk analysis
        if st.button("새로운 리스크 분석 시작", help="현재 대화를 초기화하고 새로운 리스크 분석을 시작합니다."):
            st.session_state.messages = []
            st.session_state.risk_analysis_history = [] # Clear past risk reports for a fresh start
            st.session_state.session_id = str(uuid.uuid4()) # Generate new session ID
            st.rerun()

        st.markdown("---")
        st.subheader("📈 과거 리스크 분석 보고서")
        if st.session_state.risk_analysis_history:
            for i, report in enumerate(st.session_state.risk_analysis_history):
                analysis_id = report.get("analysis_id", "N/A")[:8]
                overall_risk = report.get("risk_scoring", {}).get("overall_risk_level", "Unknown")
                timestamp = report.get("timestamp", "N/A")
                
                with st.expander(f"보고서 ID: {analysis_id} ({overall_risk})"):
                    st.write(f"**생성 시간:** {timestamp}")
                    display_risk_report(report)
        else:
            st.info("아직 완료된 리스크 분석 보고서가 없습니다.")

        st.markdown("---")
        st.markdown("### 📊 통계")
        st.metric("총 메시지 수", len(st.session_state.messages))
        st.metric("완료된 리스크 보고서", len(st.session_state.risk_analysis_history))

    # --- Main Area ---
    st.title("기업 리스크 관리 시뮬레이션")
    st.markdown(f"""
        <div style="font-size: 1.1em; color: #555;">
            {AGENT_PERSONA['feedback_style']}
        </div>
        <br>
    """, unsafe_allow_html=True)

    # Display chat messages
    chat_placeholder = st.container()

    with chat_placeholder:
        for message in st.session_state.messages:
            if message["role"] == "report": # Custom role for reports
                display_risk_report(message["content"])
            else:
                display_message(message["role"], message["content"])

    # User input
    if prompt := st.chat_input("리스크 상황을 입력해주세요... (예: 선적이 늦어져서 페널티가 발생할 것 같아요)", key="user_input_prompt"):
        # Add user message to history
        st.session_state.messages.append({"role": "user", "content": prompt})
        with chat_placeholder:
            display_message("user", prompt)

        # AI 응답
        with chat_placeholder:
            with st.spinner("AI가 리스크를 분석 중입니다..."):
                response_data = call_api("chat", 
                                         session_id=st.session_state.session_id, # Pass session_id
                                         data={
                                             "message": prompt,
                                             # "context": {"mode": "riskmanaging"} # Orchestrator will determine mode
                                         })

                if response_data:
                    response_type = response_data.get("type")
                    response_message = response_data.get("message")
                    
                    if response_type == "report":
                        report_content = response_data.get("report", {})
                        if report_content:
                            # Add timestamp to report for history
                            report_content["timestamp"] = time.strftime("%Y-%m-%d %H:%M:%S")

                            st.session_state.messages.append({"role": "report", "content": report_content})
                            st.session_state.risk_analysis_history.append(report_content)
                            
                            display_risk_report(report_content)
                            st.toast("✅ 리스크 분석 보고서가 생성되었습니다!", icon="🛡️")
                        else:
                            st.error("응답에 리포트 데이터가 없습니다.")
                            st.session_state.messages.append({"role": "assistant", "content": "보고서 데이터가 없습니다."})
                            display_message("assistant", "보고서 데이터가 없습니다.")
                    elif response_type == "chat":
                        st.session_state.messages.append({"role": "assistant", "content": response_message})
                        display_message("assistant", response_message)
                    elif response_type == "error":
                        st.error(f"백엔드 오류: {response_message}")
                        st.session_state.messages.append({"role": "assistant", "content": f"오류: {response_message}"})
                        display_message("assistant", f"오류: {response_message}")
                    else:
                        st.error(f"알 수 없는 응답 타입: {response_type}")
                        st.session_state.messages.append({"role": "assistant", "content": f"알 수 없는 응답 타입: {response_type}"})
                        display_message("assistant", f"알 수 없는 응답 타입: {response_type}")
                else:
                    st.error("서버와 통신할 수 없습니다. 백엔드 서버가 실행 중인지 확인해주세요.")

if __name__ == "__main__":
    main()
