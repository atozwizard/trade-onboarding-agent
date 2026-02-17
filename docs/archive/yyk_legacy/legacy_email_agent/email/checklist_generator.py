"""
Checklist Generator - 5W1H 체크리스트 생성

책임:
- 이메일 내용에서 5W1H 요소 검증
- 키워드 기반 체크리스트 생성
- 마크다운 포맷 체크리스트 반환
"""
from typing import List, Dict


class ChecklistGenerator:
    """5W1H 체크리스트 생성기"""

    # 체크 항목 정의
    CHECK_ITEMS = [
        {
            "item": "제품/서비스 정보 명시",
            "keywords": ["product", "item", "service", "goods", "equipment", "material"],
        },
        {
            "item": "수량/사양 명시",
            "keywords": ["quantity", "unit", "pcs", "spec", "specification", "model", "ton", "kg"],
        },
        {
            "item": "납기/기한 명시",
            "keywords": ["delivery", "deadline", "date", "schedule", "shipment", "by", "until"],
        },
        {
            "item": "Incoterms 포함",
            "keywords": ["fob", "cif", "exw", "ddp", "ddu", "incoterm"],
        },
        {
            "item": "결제 조건 포함",
            "keywords": ["payment", "t/t", "l/c", "deposit", "balance", "bank", "wire transfer"],
        }
    ]

    @classmethod
    def generate(cls, email_content: str) -> str:
        """
        이메일 내용을 분석하여 5W1H 체크리스트 생성

        Args:
            email_content: 생성된 이메일 전문

        Returns:
            체크리스트 (마크다운 형식)
        """
        email_lower = email_content.lower()

        # 키워드 기반 체크
        checks = []
        for item_config in cls.CHECK_ITEMS:
            checked = any(kw in email_lower for kw in item_config["keywords"])
            checks.append({
                "item": item_config["item"],
                "checked": checked
            })

        # 마크다운 포맷팅
        checklist_lines = []
        for check in checks:
            icon = "✅" if check["checked"] else "⚠️"
            status = "포함됨" if check["checked"] else "확인 필요"
            checklist_lines.append(f"- {icon} **{check['item']}**: {status}")

        return "\n".join(checklist_lines)
