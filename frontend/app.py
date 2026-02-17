import json
import time
import uuid
from typing import Any, Dict, Iterable, List, Optional, Tuple

import requests
import streamlit as st

# API 설정
API_BASE_URL = "http://localhost:8000/api"

# Define risk level color map based on config.py (Korean names for display)
RISK_COLOR_MAP = {
    "critical": "#D32F2F",
    "high": "#F57C00",
    "medium": "#FBC02D",
    "low": "#1976D2",
    "passthrough": "#388E3C",
}

# Persona configuration from backend for consistent tone
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
    initial_sidebar_state="expanded",
)

st.markdown(
    """
<style>
    .main .block-container {
        padding-top: 1.5rem;
        padding-bottom: 1.5rem;
    }
    .risk-badge {
        display: inline-block;
        padding: 0.25rem 0.65rem;
        border-radius: 999px;
        color: white;
        font-weight: 700;
        font-size: 0.9rem;
    }
    .risk-summary-box {
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        padding: 0.75rem;
    }
</style>
""",
    unsafe_allow_html=True,
)


def _to_float(value: Any) -> Optional[float]:
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _as_text_list(value: Any) -> List[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return []


def _dedupe_preserve_order(items: Iterable[str]) -> List[str]:
    seen = set()
    result: List[str] = []
    for item in items:
        if item and item not in seen:
            seen.add(item)
            result.append(item)
    return result


def _normalize_factor_items(report_data: Dict[str, Any]) -> List[Tuple[str, Dict[str, Any]]]:
    scoring = report_data.get("risk_scoring", {}) or {}
    raw_factors = scoring.get("risk_factors") or report_data.get("risk_factors", {})

    items: List[Tuple[str, Any]]
    if isinstance(raw_factors, dict):
        items = list(raw_factors.items())
    elif isinstance(raw_factors, list):
        items = [(f"factor_{i}", factor) for i, factor in enumerate(raw_factors)]
    else:
        items = []

    normalized_items: List[Tuple[str, Dict[str, Any]]] = []
    for default_name, factor_data in items:
        if not isinstance(factor_data, dict):
            continue

        impact = factor_data.get("impact", 0)
        likelihood = factor_data.get("likelihood", 0)
        score = _to_float(factor_data.get("score"))
        if score is None:
            score = _to_float(factor_data.get("risk_score"))
        if score is None and isinstance(impact, (int, float)) and isinstance(likelihood, (int, float)):
            score = float(impact * likelihood)
        if score is None:
            score = 0.0

        name_kr = (
            factor_data.get("name_kr")
            or factor_data.get("name")
            or default_name
        )
        reason = factor_data.get("reason") or factor_data.get("reasoning") or ""

        normalized_items.append(
            (
                str(name_kr),
                {
                    **factor_data,
                    "name_kr": str(name_kr),
                    "score": float(score),
                    "reason": str(reason),
                    "mitigation_suggestions": _as_text_list(
                        factor_data.get("mitigation_suggestions")
                    ),
                },
            )
        )

    return normalized_items


def _build_suggested_actions(report_data: Dict[str, Any], factor_items: List[Tuple[str, Dict[str, Any]]]) -> List[str]:
    actions = _as_text_list(report_data.get("suggested_actions"))
    if actions:
        return _dedupe_preserve_order(actions)

    prevention_strategy = report_data.get("prevention_strategy", {})
    control_gap_analysis = report_data.get("control_gap_analysis", {})

    if isinstance(prevention_strategy, dict):
        actions.extend(_as_text_list(prevention_strategy.get("short_term")))
        actions.extend(_as_text_list(prevention_strategy.get("long_term")))
    if isinstance(control_gap_analysis, dict):
        actions.extend(_as_text_list(control_gap_analysis.get("recommendations")))

    for _, factor in factor_items:
        actions.extend(_as_text_list(factor.get("mitigation_suggestions")))

    return _dedupe_preserve_order(actions)


def _format_similar_case(case: Any) -> str:
    if not isinstance(case, dict):
        return str(case)

    content = str(case.get("content", "")).strip() or "(내용 없음)"
    source = str(case.get("source", "unknown")).strip() or "unknown"
    category = str(case.get("category", "")).strip()
    distance = case.get("distance")

    parts = [content, f"출처: {source}"]
    if category:
        parts.append(f"분류: {category}")
    if isinstance(distance, (int, float)):
        parts.append(f"유사도 거리: {distance:.3f}")

    topic = case.get("topic", [])
    if isinstance(topic, list) and topic:
        parts.append(f"토픽: {', '.join(str(item) for item in topic)}")

    return " | ".join(parts)


def _render_report_summary_in_sidebar(report_data: Dict[str, Any]) -> None:
    scoring = report_data.get("risk_scoring", {}) or {}
    summary = (
        report_data.get("response_summary")
        or report_data.get("input_summary")
        or scoring.get("overall_assessment")
        or "요약 정보 없음"
    )
    suggested_actions = _as_text_list(report_data.get("suggested_actions"))
    if not suggested_actions:
        prevention_strategy = report_data.get("prevention_strategy", {})
        if isinstance(prevention_strategy, dict):
            suggested_actions.extend(_as_text_list(prevention_strategy.get("short_term")))

    st.markdown(f"<div class='risk-summary-box'>{summary}</div>", unsafe_allow_html=True)
    if suggested_actions:
        st.caption("우선 조치")
        for action in suggested_actions[:2]:
            st.markdown(f"- {action}")


def _init_session_state() -> None:
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "risk_analysis_history" not in st.session_state:
        st.session_state.risk_analysis_history = []
    if "session_id" not in st.session_state:
        st.session_state.session_id = str(uuid.uuid4())
    if "chat_mode" not in st.session_state:
        st.session_state.chat_mode = "auto"


def call_api(endpoint: str, session_id: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Call backend API"""
    try:
        payload = dict(data)
        payload["session_id"] = session_id
        response = requests.post(f"{API_BASE_URL}/{endpoint}", json=payload)
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


def display_message(role: str, content: str) -> None:
    """Render single chat message using Streamlit native chat components."""
    if role == "user":
        with st.chat_message("user", avatar="👤"):
            st.write(str(content))
    else:
        with st.chat_message("assistant", avatar="🤖"):
            st.write(str(content))


def display_risk_report(report_data: Dict[str, Any]) -> None:
    """Render risk report in a stable Streamlit layout without HTML wrapper hacks."""
    scoring = report_data.get("risk_scoring", {}) or {}
    analysis_id = str(report_data.get("analysis_id", "N/A"))
    overall_risk_level = str(scoring.get("overall_risk_level", "Unknown"))
    response_summary = (
        report_data.get("response_summary")
        or report_data.get("input_summary")
        or scoring.get("overall_assessment")
        or "요약 정보가 없습니다."
    )

    factor_items = _normalize_factor_items(report_data)

    overall_risk_score = _to_float(scoring.get("overall_risk_score"))
    if overall_risk_score is None:
        if factor_items:
            overall_risk_score = sum(item[1]["score"] for item in factor_items) / len(factor_items)
        else:
            overall_risk_score = 0.0

    suggested_actions = _build_suggested_actions(report_data, factor_items)
    similar_cases = report_data.get("similar_cases", [])
    evidence_sources = _as_text_list(report_data.get("evidence_sources"))

    badge_color = RISK_COLOR_MAP.get(overall_risk_level.lower(), "#607D8B")

    with st.container(border=True):
        left_col, right_col = st.columns([2.4, 1.0])
        with left_col:
            st.markdown(f"#### 리스크 분석 보고서 (ID: {analysis_id[:8]})")
            st.markdown(
                (
                    f"<span class='risk-badge' style='background:{badge_color};'>"
                    f"종합 리스크 레벨: {overall_risk_level}"
                    "</span>"
                ),
                unsafe_allow_html=True,
            )
        with right_col:
            st.metric("종합 점수", f"{overall_risk_score:.1f}")

        st.markdown("##### 리스크 요약")
        st.write(str(response_summary))

        st.markdown("##### 주요 리스크 요인 분석")
        if factor_items:
            for factor_name, factor_data in factor_items:
                impact = factor_data.get("impact", 0)
                likelihood = factor_data.get("likelihood", 0)
                score = float(factor_data.get("score", 0.0))
                description = str(factor_data.get("description", "")).strip()
                reason = str(factor_data.get("reason", "")).strip()
                mitigations = _as_text_list(factor_data.get("mitigation_suggestions"))

                expander_title = (
                    f"{factor_name} | 영향 {impact}, 가능성 {likelihood}, 점수 {score:.1f}"
                )
                with st.expander(expander_title):
                    if description:
                        st.caption(description)
                    st.write(reason if reason else "근거 정보가 제공되지 않았습니다.")
                    if mitigations:
                        st.caption("완화 방안")
                        for item in mitigations:
                            st.markdown(f"- {item}")
                    st.progress(min(score / 25.0, 1.0))
        else:
            st.info("리스크 요인 정보가 없습니다.")

        st.markdown("##### 제안하는 조치")
        if suggested_actions:
            for action in suggested_actions:
                st.markdown(f"- {action}")
        else:
            st.info("현재 상황에 대한 제안 조치가 없습니다.")

        st.markdown("##### 유사 사례 및 근거 자료")
        if isinstance(similar_cases, list) and similar_cases:
            st.caption("유사 사례")
            for case in similar_cases:
                st.markdown(f"- {_format_similar_case(case)}")
        if evidence_sources:
            st.caption("근거 자료")
            for source in evidence_sources:
                st.markdown(f"- {source}")
        if not similar_cases and not evidence_sources:
            st.info("관련 유사 사례 또는 근거 자료를 찾을 수 없습니다.")


def _render_chat_history() -> None:
    for message in st.session_state.messages:
        role = message.get("role")
        content = message.get("content")

        if role == "report" and isinstance(content, dict):
            with st.chat_message("assistant", avatar="🛡️"):
                display_risk_report(content)
        elif role == "user":
            display_message("user", str(content))
        else:
            display_message("assistant", str(content))


def _handle_user_prompt(prompt: str) -> None:
    st.session_state.messages.append({"role": "user", "content": prompt})

    request_payload: Dict[str, Any] = {"message": prompt}
    if st.session_state.chat_mode != "auto":
        request_payload["context"] = {"mode": st.session_state.chat_mode}

    with st.spinner("AI가 응답을 생성 중입니다..."):
        response_data = call_api(
            "chat",
            session_id=st.session_state.session_id,
            data=request_payload,
        )

    if not response_data:
        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": "서버와 통신할 수 없습니다. 백엔드 서버가 실행 중인지 확인해주세요.",
            }
        )
        return

    response_type = response_data.get("type")
    response_message = str(response_data.get("message", "")).strip()

    if response_type == "report":
        report_content = response_data.get("report", {})
        if isinstance(report_content, dict) and report_content:
            report_copy = dict(report_content)
            report_copy["timestamp"] = time.strftime("%Y-%m-%d %H:%M:%S")
            st.session_state.messages.append({"role": "report", "content": report_copy})
            st.session_state.risk_analysis_history.append(report_copy)
        else:
            st.session_state.messages.append(
                {"role": "assistant", "content": "보고서 데이터가 없습니다."}
            )
    elif response_type == "chat":
        st.session_state.messages.append(
            {"role": "assistant", "content": response_message or "응답이 비어 있습니다."}
        )
    elif response_type == "error":
        st.session_state.messages.append(
            {"role": "assistant", "content": f"오류: {response_message}"}
        )
    else:
        st.session_state.messages.append(
            {"role": "assistant", "content": f"알 수 없는 응답 타입: {response_type}"}
        )


def main() -> None:
    """Main application"""
    _init_session_state()

    # Sidebar
    with st.sidebar:
        st.title("기업 리스크 관리 AI")
        st.markdown("---")

        st.subheader("테스트 라우팅 모드")
        mode_options = {
            "자동 (Orchestrator 판단)": "auto",
            "리스크 분석 강제": "riskmanaging",
            "퀴즈 강제": "quiz",
            "이메일 강제": "email",
            "기본 대화 강제": "default_chat",
        }
        current_mode = st.session_state.chat_mode
        selected_mode_label = st.selectbox(
            "mode",
            list(mode_options.keys()),
            index=list(mode_options.values()).index(current_mode)
            if current_mode in mode_options.values()
            else 0,
        )
        st.session_state.chat_mode = mode_options[selected_mode_label]

        if st.session_state.chat_mode == "auto":
            st.caption("React 전환 시에도 context.mode를 생략하면 자동 라우팅됩니다.")
        else:
            st.caption(f"현재 요청은 context.mode={st.session_state.chat_mode}로 전송됩니다.")

        st.markdown("---")
        if st.button("새로운 리스크 분석 시작", help="현재 대화를 초기화하고 새로운 분석을 시작합니다."):
            st.session_state.messages = []
            st.session_state.risk_analysis_history = []
            st.session_state.session_id = str(uuid.uuid4())
            st.rerun()

        st.markdown("---")
        st.subheader("과거 리스크 분석 보고서")
        if st.session_state.risk_analysis_history:
            for report in st.session_state.risk_analysis_history:
                analysis_id = str(report.get("analysis_id", "N/A"))[:8]
                risk_level = (
                    report.get("risk_scoring", {}).get("overall_risk_level", "Unknown")
                )
                timestamp = report.get("timestamp", "N/A")
                with st.expander(f"보고서 ID: {analysis_id} ({risk_level})"):
                    st.caption(f"생성 시간: {timestamp}")
                    _render_report_summary_in_sidebar(report)
        else:
            st.info("아직 완료된 리스크 분석 보고서가 없습니다.")

        st.markdown("---")
        st.markdown("### 통계")
        st.metric("총 메시지 수", len(st.session_state.messages))
        st.metric("완료된 리스크 보고서", len(st.session_state.risk_analysis_history))

    # Main area
    st.title("기업 리스크 관리 시뮬레이션")
    st.caption(AGENT_PERSONA["feedback_style"])

    _render_chat_history()

    prompt = st.chat_input(
        "리스크 상황을 입력해주세요... (예: 선적이 늦어져서 페널티가 발생할 것 같아요)",
        key="user_input_prompt",
    )
    if prompt:
        _handle_user_prompt(prompt)
        st.rerun()


if __name__ == "__main__":
    main()

