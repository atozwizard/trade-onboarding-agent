"""
Unit Validator - 무역 단위 검증

책임:
- 무역 단위 추출 (톤, kg, CBM, container 등)
- 단위 일관성 검증
- 표준 단위 제안
"""

import re
import logging
from typing import Dict, List, Any


class UnitValidator:
    """무역 단위 검증 서비스"""

    # 유효한 단위 정의
    VALID_UNITS = {
        "weight": {
            "ton": ["ton", "mt", "metric ton", "tons"],
            "kg": ["kg", "kilogram", "kilograms"],
            "lbs": ["lbs", "pounds", "lb"]
        },
        "volume": {
            "cbm": ["cbm", "m3", "cubic meter", "cubic meters"],
            "cft": ["cft", "cubic feet", "cubic ft"]
        },
        "container": {
            "20ft": ["20ft", "20'", "20 ft", "20-ft"],
            "40ft": ["40ft", "40'", "40 ft", "40-ft"],
            "40hc": ["40hc", "40' hc", "40ft hc", "40-ft hc"]
        }
    }

    # 단위 변환 비율
    CONVERSION = {
        "ton_to_kg": 1000,
        "mt_to_kg": 1000,
        "cbm_to_cft": 35.3147
    }

    def __init__(self):
        """초기화"""
        self._logger = logging.getLogger(__name__)

    def validate(self, email_content: str) -> Dict[str, Any]:
        """
        이메일 내 단위 검증

        Args:
            email_content: 이메일 본문

        Returns:
            {
                "inconsistencies": [
                    {
                        "text": "20ton and 20000kg",
                        "issue": "mixed units for same item",
                        "suggestion": "Use consistent unit (prefer MT)"
                    }
                ],
                "standardized": "20 MT (20,000 kg)",
                "unit_summary": {
                    "weight": ["20 ton", "20000 kg"],
                    "volume": ["15 CBM"],
                    "container": ["1x40HC"]
                }
            }
        """
        try:
            # 1. 단위 추출
            weight_units = self._extract_weight_units(email_content)
            volume_units = self._extract_volume_units(email_content)
            container_units = self._extract_container_units(email_content)

            # 2. 일관성 검증
            inconsistencies = self._check_inconsistencies(
                weight_units, volume_units, container_units, email_content
            )

            # 3. 표준화 제안
            standardized = self._standardize_units(weight_units, volume_units, container_units)

            return {
                "inconsistencies": inconsistencies,
                "standardized": standardized,
                "unit_summary": {
                    "weight": weight_units,
                    "volume": volume_units,
                    "container": container_units
                }
            }

        except Exception as e:
            self._logger.error(f"Unit validation error: {e}")
            return {
                "inconsistencies": [],
                "standardized": "",
                "unit_summary": {
                    "weight": [],
                    "volume": [],
                    "container": []
                }
            }

    def _extract_weight_units(self, text: str) -> List[str]:
        """
        무게 단위 추출

        Args:
            text: 이메일 본문

        Returns:
            무게 단위 리스트 (예: ["20 ton", "20000 kg"])
        """
        # 패턴: 숫자 + 공백(선택) + 쉼표(선택) + 단위
        # 예: 20ton, 20,000kg, 20 MT
        pattern = r'\d+(?:,\d{3})*(?:\.\d+)?[\s,]*(?:ton|tons|mt|metric\s+ton|kg|kilogram|kilograms|lbs|pounds|lb)\b'
        matches = re.findall(pattern, text, re.IGNORECASE)

        # 중복 제거 및 정규화
        normalized = []
        for match in matches:
            # 공백 정규화
            normalized_match = re.sub(r'\s+', ' ', match.strip())
            if normalized_match not in normalized:
                normalized.append(normalized_match)

        return normalized

    def _extract_volume_units(self, text: str) -> List[str]:
        """
        부피 단위 추출

        Args:
            text: 이메일 본문

        Returns:
            부피 단위 리스트 (예: ["15 CBM"])
        """
        # 패턴: 숫자 + 공백(선택) + 부피 단위
        pattern = r'\d+(?:,\d{3})*(?:\.\d+)?[\s,]*(?:cbm|m3|cft|cubic\s+(?:meter|meters|feet|ft))\b'
        matches = re.findall(pattern, text, re.IGNORECASE)

        normalized = []
        for match in matches:
            normalized_match = re.sub(r'\s+', ' ', match.strip())
            if normalized_match not in normalized:
                normalized.append(normalized_match)

        return normalized

    def _extract_container_units(self, text: str) -> List[str]:
        """
        컨테이너 단위 추출

        Args:
            text: 이메일 본문

        Returns:
            컨테이너 단위 리스트 (예: ["1x40HC"])
        """
        # 패턴: 숫자 + x + 컨테이너 크기
        # 예: 1x20ft, 2x40HC, 1 x 40'
        pattern = r'\d+[\s]*x[\s]*(?:20|40)[\s]*(?:ft|\')?[\s]*(?:hc)?\b'
        matches = re.findall(pattern, text, re.IGNORECASE)

        normalized = []
        for match in matches:
            # 공백 제거하고 대문자로 통일
            normalized_match = match.replace(' ', '').upper()
            if normalized_match not in normalized:
                normalized.append(normalized_match)

        return normalized

    def _check_inconsistencies(
        self,
        weight_units: List[str],
        volume_units: List[str],
        container_units: List[str],
        email_content: str
    ) -> List[Dict]:
        """
        단위 일관성 검증

        Args:
            weight_units: 무게 단위 리스트
            volume_units: 부피 단위 리스트
            container_units: 컨테이너 단위 리스트
            email_content: 이메일 본문

        Returns:
            불일치 리스트
        """
        inconsistencies = []

        # 1. 무게 단위 혼용 체크
        if len(weight_units) > 1:
            has_ton = any(
                re.search(r'(?<![a-zA-Z])(?:ton|tons|mt|metric\s+ton)\b', unit, re.IGNORECASE)
                for unit in weight_units
            )
            has_kg = any(
                re.search(r'(?<![a-zA-Z])(?:kg|kilogram|kilograms)\b', unit, re.IGNORECASE)
                for unit in weight_units
            )

            if has_ton and has_kg:
                # 동일한 값인지 확인 (예: 20 ton = 20000 kg)
                if not self._is_equivalent_weights(weight_units):
                    inconsistencies.append({
                        "text": f"{', '.join(weight_units)}",
                        "issue": "혼용된 무게 단위 (ton과 kg)",
                        "suggestion": "일관된 단위 사용 권장 (MT 선호)",
                        "severity": "medium"
                    })

        # 2. 부피 단위 혼용 체크
        if len(volume_units) > 1:
            has_cbm = any(
                re.search(r'(?<![a-zA-Z])(?:cbm|m3|cubic\s+meter|cubic\s+meters)\b', unit, re.IGNORECASE)
                for unit in volume_units
            )
            has_cft = any(
                re.search(r'(?<![a-zA-Z])(?:cft|cubic\s+feet|cubic\s+ft)\b', unit, re.IGNORECASE)
                for unit in volume_units
            )

            if has_cbm and has_cft:
                inconsistencies.append({
                    "text": f"{', '.join(volume_units)}",
                    "issue": "혼용된 부피 단위 (CBM과 CFT)",
                    "suggestion": "일관된 단위 사용 권장 (CBM 선호)",
                    "severity": "medium"
                })

        # 3. 숫자 형식 불일치 체크 (쉼표 사용 여부)
        all_units = weight_units + volume_units
        if all_units:
            has_comma = any(',' in unit for unit in all_units)
            has_no_comma = any(',' not in unit and re.search(r'\d{4,}', unit) for unit in all_units)

            if has_comma and has_no_comma:
                inconsistencies.append({
                    "text": f"{', '.join(all_units[:3])}{'...' if len(all_units) > 3 else ''}",
                    "issue": "숫자 형식 불일치 (쉼표 사용 여부)",
                    "suggestion": "큰 숫자에는 일관되게 쉼표 사용 (예: 20,000)",
                    "severity": "low"
                })

        return inconsistencies

    def _is_equivalent_weights(self, weight_units: List[str]) -> bool:
        """
        무게 단위가 동일한 값인지 확인 (예: 20 ton = 20,000 kg)

        Args:
            weight_units: 무게 단위 리스트

        Returns:
            동일한 값이면 True
        """
        try:
            # 모든 단위를 kg로 변환
            kg_values = []

            for unit in weight_units:
                # 숫자 추출
                num_match = re.search(r'\d+(?:,\d{3})*(?:\.\d+)?', unit)
                if not num_match:
                    continue

                value_str = num_match.group().replace(',', '')
                value = float(value_str)

                # 단위 확인하여 kg로 변환
                if re.search(r'(?<![a-zA-Z])(?:ton|tons|mt|metric\s+ton)\b', unit, re.IGNORECASE):
                    kg_values.append(value * 1000)
                elif re.search(r'(?<![a-zA-Z])(?:kg|kilogram|kilograms)\b', unit, re.IGNORECASE):
                    kg_values.append(value)
                elif re.search(r'(?<![a-zA-Z])(?:lb|lbs|pound|pounds)\b', unit, re.IGNORECASE):
                    kg_values.append(value * 0.453592)

            # 모든 값이 동일한지 확인 (5% 오차 허용)
            if len(kg_values) >= 2:
                base_value = kg_values[0]
                if base_value == 0:
                    return all(val == 0 for val in kg_values[1:])
                for val in kg_values[1:]:
                    if abs(val - base_value) / base_value > 0.05:
                        return False
                return True

        except Exception as e:
            self._logger.warning(f"Weight equivalence check error: {e}")

        return False

    def _standardize_units(
        self,
        weight_units: List[str],
        volume_units: List[str],
        container_units: List[str]
    ) -> str:
        """
        단위 표준화 제안

        Args:
            weight_units: 무게 단위 리스트
            volume_units: 부피 단위 리스트
            container_units: 컨테이너 단위 리스트

        Returns:
            표준화된 단위 문자열 (예: "20 MT (20,000 kg), 15 CBM, 1x40HC")
        """
        parts = []

        # 1. 무게 표준화 (MT 우선, kg 병기)
        if weight_units:
            first_weight = weight_units[0]

            # 숫자 추출
            num_match = re.search(r'\d+(?:,\d{3})*(?:\.\d+)?', first_weight)
            if num_match:
                value_str = num_match.group().replace(',', '')
                value = float(value_str)

                # 단위 확인
                if re.search(r'(?<![a-zA-Z])(?:ton|tons|mt|metric\s+ton)\b', first_weight, re.IGNORECASE):
                    # 이미 톤 단위
                    kg_value = int(value * 1000)
                    parts.append(f"{int(value)} MT ({kg_value:,} kg)")
                elif re.search(r'(?<![a-zA-Z])(?:kg|kilogram|kilograms)\b', first_weight, re.IGNORECASE):
                    # kg 단위 -> MT로 변환
                    if value >= 1000:
                        mt_value = value / 1000
                        parts.append(f"{mt_value:.1f} MT ({int(value):,} kg)")
                    else:
                        parts.append(f"{int(value)} kg")
                else:
                    parts.append(first_weight)

        # 2. 부피 표준화 (CBM 우선)
        if volume_units:
            first_volume = volume_units[0]

            # CFT -> CBM 변환 제안
            if re.search(r'(?<![a-zA-Z])(?:cft|cubic\s+feet|cubic\s+ft)\b', first_volume, re.IGNORECASE):
                num_match = re.search(r'\d+(?:,\d{3})*(?:\.\d+)?', first_volume)
                if num_match:
                    value = float(num_match.group().replace(',', ''))
                    cbm_value = value / 35.3147
                    parts.append(f"{cbm_value:.2f} CBM (≈ {int(value)} CFT)")
            else:
                parts.append(first_volume.upper())

        # 3. 컨테이너 표준화
        if container_units:
            parts.append(container_units[0])

        return ", ".join(parts) if parts else ""
