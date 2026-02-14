import json
from typing import Any, Dict

def normalize_response(raw: Any) -> Dict[str, Any]:
    """
    모든 agent 응답을 통일된 ChatResponse dict로 변환
    """

    # 이미 dict
    if isinstance(raw, dict):
        if "type" in raw:
            return raw

        message_content = raw.get("response") or raw.get("message") or str(raw)
        report_content = raw.get("report") # This would be None from RiskManagingAgentResponse.model_dump()

        # Try to parse message_content as JSON to detect reports
        if isinstance(message_content, str):
            try:
                parsed_message = json.loads(message_content)
                if isinstance(parsed_message, dict) and "analysis_id" in parsed_message: # Heuristic for a report
                    return {
                        "type": "report",
                        "message": parsed_message.get("summary", "보고서가 생성되었습니다."), # Use summary from report if available
                        "report": parsed_message,
                        "meta": {}
                    }
            except json.JSONDecodeError:
                pass # Not a JSON string, or not a report JSON

        return {
            "type": "chat",
            "message": message_content,
            "report": report_content,
            "meta": {}
        }

    # 문자열일 경우
    if isinstance(raw, str):
        raw = raw.strip()

        # JSON string인지 시도
        try:
            parsed = json.loads(raw)

            if isinstance(parsed, dict):
                return {
                    "type": "report",
                    "message": parsed.get("summary", "report generated"),
                    "report": parsed,
                    "meta": {}
                }

        except Exception:
            pass

        # 일반 문자열
        return {
            "type": "chat",
            "message": raw,
            "report": None,
            "meta": {}
        }

    # fallback
    return {
        "type": "chat",
        "message": str(raw),
        "report": None,
        "meta": {}
    }
