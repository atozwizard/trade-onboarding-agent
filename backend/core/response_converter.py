import json
from typing import Any, Dict

def normalize_response(raw: Any) -> Dict[str, Any]:
    """
    모든 agent 응답을 통일된 ChatResponse dict로 변환
    """

    # 기본 구조 설정
    default_report = {
        "analysis_id": "N/A",
        "risk_scoring": {
            "overall_risk_level": "Unknown",
            "overall_risk_score": 0.0,
            "risk_factors": {} # app.py가 items()를 쓸 수 있게 dict로 유지
        },
        "response_summary": "요약 정보가 없습니다.",
        "suggested_actions": [],
        "similar_cases": [],
        "evidence_sources": []
    }

    # Identify if it's a report or a simple chat message
    extracted_report_dict = None
    chat_message_content = str(raw) # Default to raw as string

    if isinstance(raw, dict):
        if "type" in raw: # Already normalized ChatResponse
            return raw
        
        # Check for report data in 'report' key
        if isinstance(raw.get("report"), dict):
            extracted_report_dict = raw.get("report")
        # Check for report data or message in 'response' key
        elif raw.get("response") is not None:
            if isinstance(raw.get("response"), dict): # Agent returned report dict directly in 'response'
                extracted_report_dict = raw.get("response")
            elif isinstance(raw.get("response"), str):
                chat_message_content = raw.get("response")
                try: # Try to parse 'response' string as JSON report
                    parsed_str = json.loads(chat_message_content)
                    if isinstance(parsed_str, dict) and "analysis_id" in parsed_str:
                        extracted_report_dict = parsed_str
                except json.JSONDecodeError:
                    pass
        # Check for message in 'message' key (fallback for some agent types)
        elif isinstance(raw.get("message"), str):
            chat_message_content = raw.get("message")
            try: # Try to parse 'message' string as JSON report
                parsed_str = json.loads(chat_message_content)
                if isinstance(parsed_str, dict) and "analysis_id" in parsed_str:
                    extracted_report_dict = parsed_str
            except json.JSONDecodeError:
                pass
        else: # If raw is a dict but no specific keys, use raw as chat message
            chat_message_content = str(raw)

    elif isinstance(raw, str): # Raw is a string
        chat_message_content = raw
        try: # Try to parse raw string as JSON report
            parsed_str = json.loads(raw)
            if isinstance(parsed_str, dict) and "analysis_id" in parsed_str:
                extracted_report_dict = parsed_str
        except json.JSONDecodeError:
            pass

    # Process if a report dict was successfully extracted
    if extracted_report_dict:
        report_source = extracted_report_dict

        # 2. 데이터 매핑 (app.py의 변수명에 맞춤)
        mapping = {
            "analysis_id": report_source.get("analysis_id") or report_source.get("id"),
            "response_summary": report_source.get("summary") or report_source.get("response_summary"),
            "suggested_actions": report_source.get("recommendations") or report_source.get("suggested_actions", []),
            "similar_cases": report_source.get("similar_cases", []),
            "evidence_sources": report_source.get("evidence_sources", [])
        }
        default_report.update({k: v for k, v in mapping.items() if v is not None})

        # 3. 리스크 스코어링 및 요인(Factors) 정규화
        scoring_source = report_source.get("risk_scoring") or report_source
        if isinstance(scoring_source, dict):
            default_report["risk_scoring"]["overall_risk_level"] = scoring_source.get("overall_risk_level", "Unknown")
            overall_score = scoring_source.get("overall_risk_score")
            if isinstance(overall_score, (int, float)):
                default_report["risk_scoring"]["overall_risk_score"] = float(overall_score)
            else:
                default_report["risk_scoring"]["overall_risk_score"] = 0.0
            
            raw_factors = scoring_source.get("risk_factors", [])
            
            norm_factors = {}
            if isinstance(raw_factors, list):
                for i, f in enumerate(raw_factors):
                    if isinstance(f, dict):
                        key = f.get("name", f.get("name_kr", f"factor_{i}"))
                        norm_factors[key] = f
            elif isinstance(raw_factors, dict):
                norm_factors = raw_factors
                
            default_report["risk_scoring"]["risk_factors"] = norm_factors

        # Return as report
        return {
            "type": "report",
            "message": default_report["response_summary"],
            "report": default_report,
            "meta": {}
        }
    else:
        # It's a chat message
        return {
            "type": "chat",
            "message": chat_message_content,
            "report": None,
            "meta": {}
        }
