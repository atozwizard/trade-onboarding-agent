from __future__ import annotations

from typing import Any, Dict, List

import requests
from streamlit.testing.v1 import AppTest


class _DummyResponse:
    def __init__(self, payload: Dict[str, Any], status_code: int = 200):
        self._payload = payload
        self.status_code = status_code
        self.text = str(payload)

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}")

    def json(self) -> Dict[str, Any]:
        return self._payload


def _markdown_values(app: AppTest) -> List[str]:
    return [str(item.value) for item in app.markdown]


def _metric_value(app: AppTest, label: str) -> str | None:
    for metric in app.metric:
        if metric.label == label:
            return metric.value
    return None


def test_ui_renders_risk_report_without_raw_dict_text(monkeypatch):
    payload = {
        "type": "report",
        "message": "선적 지연 리스크 요약",
        "report": {
            "analysis_id": "abf220d2",
            "input_summary": "선적 지연 리스크 요약",
            "risk_scoring": {
                "overall_risk_level": "medium",
                "risk_factors": [
                    {
                        "name": "재정적 손실",
                        "impact": 3,
                        "likelihood": 4,
                        "risk_score": 12,
                        "reasoning": "일당 0.5% 페널티로 손실이 누적됩니다.",
                        "mitigation_suggestions": ["선적 일정 재협상"],
                    }
                ],
            },
            "prevention_strategy": {"short_term": ["고객사 사전 통보"]},
            "similar_cases": [{"content": "delay penalty", "source": "cases.csv"}],
            "evidence_sources": ["cases.csv"],
        },
        "meta": {},
    }

    monkeypatch.setattr(requests, "post", lambda *a, **k: _DummyResponse(payload))

    app = AppTest.from_file("frontend/app.py")
    app.run()
    app.chat_input[0].set_value("선적이 늦어요").run()

    markdown_values = _markdown_values(app)
    assert any("리스크 분석 보고서" in value for value in markdown_values)
    assert any("선적 지연 리스크 요약" in value for value in markdown_values)
    assert any("delay penalty | 출처: cases.csv" in value for value in markdown_values)
    assert all("{'content'" not in value for value in markdown_values)

    assert _metric_value(app, "종합 점수") == "12.0"
    assert any("재정적 손실 | 영향 3, 가능성 4, 점수 12.0" == exp.label for exp in app.expander)


def test_ui_renders_chat_message_for_chat_response(monkeypatch):
    payload = {"type": "chat", "message": "일반 답변입니다.", "report": None, "meta": {}}
    monkeypatch.setattr(requests, "post", lambda *a, **k: _DummyResponse(payload))

    app = AppTest.from_file("frontend/app.py")
    app.run()
    app.chat_input[0].set_value("안녕").run()

    markdown_values = _markdown_values(app)
    assert any("일반 답변입니다." in value for value in markdown_values)
    assert _metric_value(app, "종합 점수") is None


def test_ui_sends_context_mode_when_mode_forced(monkeypatch):
    captured_payloads: List[Dict[str, Any]] = []

    def _fake_post(*args, **kwargs):
        captured_payloads.append(kwargs.get("json", {}))
        return _DummyResponse({"type": "chat", "message": "ok", "report": None, "meta": {}})

    monkeypatch.setattr(requests, "post", _fake_post)

    app = AppTest.from_file("frontend/app.py")
    app.run()
    app.selectbox[0].set_value("리스크 분석 강제").run()
    app.chat_input[0].set_value("테스트 메시지").run()

    assert captured_payloads, "API payload was not captured"
    last_payload = captured_payloads[-1]
    assert last_payload.get("context", {}).get("mode") == "riskmanaging"
    assert isinstance(last_payload.get("session_id"), str)

