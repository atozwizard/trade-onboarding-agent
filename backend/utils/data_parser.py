"""
Data Parser for TradeOnboarding Agent
Parses dummydata1.md and dummydata2.md into structured JSON files
"""

import json
import re
from pathlib import Path
from typing import List, Dict, Any


class DataParser:
    def __init__(self, raw_data_dir: str, output_dir: str):
        self.raw_data_dir = Path(raw_data_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def parse_dummydata1(self):
        """Parse dummydata1.md into structured JSON files"""
        file_path = self.raw_data_dir / "dummydata1.md"
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Parse company domain knowledge (6 fields × 20)
        company_domain = self._parse_table_section(
            content,
            start_marker="1️⃣ 회사 도메인 지식",
            end_marker="2️⃣ 회사 내부 프로세스",
            fields=["id", "term", "definition", "usage", "caution", "related_work"],
            category="company_domain"
        )
        
        # Parse internal process (5 fields × 20)
        internal_process = self._parse_table_section(
            content,
            start_marker="2️⃣ 회사 내부 프로세스",
            end_marker="3️⃣ 사고/실수 사례",
            fields=["id", "stage", "person", "input", "output"],
            category="internal_process"
        )
        
        # Parse mistakes (5 fields × 20)
        mistakes = self._parse_table_section(
            content,
            start_marker="3️⃣ 사고/실수 사례",
            end_marker="4️⃣ 대표/팀장 판단 기준",
            fields=["id", "situation", "cause", "result", "prevention"],
            category="mistakes"
        )
        
        # Parse CEO style (4 fields × 20)
        ceo_style = self._parse_table_section(
            content,
            start_marker="4️⃣ 대표/팀장 판단 기준",
            end_marker="5️⃣ 커뮤니케이션 데이터",
            fields=["id", "situation", "priority", "action"],
            category="ceo_style"
        )
        
        # Parse communication data (4 fields × 20)
        emails = self._parse_table_section(
            content,
            start_marker="5️⃣ 커뮤니케이션 데이터",
            end_marker=None,
            fields=["id", "situation", "recipient", "example"],
            category="emails"
        )
        
        # Save to JSON
        self._save_json("company_domain.json", company_domain)
        self._save_json("internal_process.json", internal_process)
        self._save_json("mistakes.json", mistakes)
        self._save_json("ceo_style.json", ceo_style)
        self._save_json("emails.json", emails)
        
        return {
            "company_domain": len(company_domain),
            "internal_process": len(internal_process),
            "mistakes": len(mistakes),
            "ceo_style": len(ceo_style),
            "emails": len(emails)
        }
    
    def parse_dummydata2(self):
        """Parse dummydata2.md into structured JSON files"""
        file_path = self.raw_data_dir / "dummydata2.md"
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Parse email logs (20 items)
        emails_new = self._parse_list_section(
            content,
            start_marker="[A] 실제 이메일 로그",
            end_marker="[B] 실제 실수 사례",
            category="emails"
        )
        
        # Parse mistakes (20 items)
        mistakes_new = self._parse_list_section(
            content,
            start_marker="[B] 실제 실수 사례",
            end_marker="[C] 대표 의사결정 스타일",
            category="mistakes"
        )
        
        # Parse CEO style (20 items)
        ceo_style_new = self._parse_list_section(
            content,
            start_marker="[C] 대표 의사결정 스타일",
            end_marker="[D] 거래 국가별 특징",
            category="ceo_style"
        )
        
        # Parse country rules (20 items)
        country_rules = self._parse_list_section(
            content,
            start_marker="[D] 거래 국가별 특징",
            end_marker="[E] 가격 협상 사례",
            category="country_rules"
        )
        
        # Parse negotiation (20 items)
        negotiation = self._parse_list_section(
            content,
            start_marker="[E] 가격 협상 사례",
            end_marker="[F] 클레임/분쟁 사례",
            category="negotiation"
        )
        
        # Parse claims (20 items)
        claims = self._parse_list_section(
            content,
            start_marker="[F] 클레임/분쟁 사례",
            end_marker="[G] 선적/서류 오류 패턴",
            category="claims"
        )
        
        # Parse document errors (20 items)
        document_errors = self._parse_list_section(
            content,
            start_marker="[G] 선적/서류 오류 패턴",
            end_marker="[H] 무역 용어 Q&A",
            category="document_errors"
        )
        
        # Parse trade Q&A (20 items)
        trade_qa = self._parse_list_section(
            content,
            start_marker="[H] 무역 용어 Q&A",
            end_marker="[I] KPI/성과 데이터",
            category="trade_qa"
        )
        
        # Parse KPI (20 items)
        kpi = self._parse_list_section(
            content,
            start_marker="[I] KPI/성과 데이터",
            end_marker="[J] 온보딩 퀴즈 샘플",
            category="kpi"
        )
        
        # Parse quiz samples (20 items)
        quiz_samples = self._parse_list_section(
            content,
            start_marker="[J] 온보딩 퀴즈 샘플",
            end_marker=None,
            category="quiz"
        )
        
        # Append to existing files
        self._append_json("emails.json", emails_new)
        self._append_json("mistakes.json", mistakes_new)
        self._append_json("ceo_style.json", ceo_style_new)
        
        # Save new files
        self._save_json("country_rules.json", country_rules)
        self._save_json("negotiation.json", negotiation)
        self._save_json("claims.json", claims)
        self._save_json("document_errors.json", document_errors)
        self._save_json("trade_qa.json", trade_qa)
        self._save_json("kpi.json", kpi)
        self._save_json("quiz_samples.json", quiz_samples)
        
        return {
            "emails_appended": len(emails_new),
            "mistakes_appended": len(mistakes_new),
            "ceo_style_appended": len(ceo_style_new),
            "country_rules": len(country_rules),
            "negotiation": len(negotiation),
            "claims": len(claims),
            "document_errors": len(document_errors),
            "trade_qa": len(trade_qa),
            "kpi": len(kpi),
            "quiz_samples": len(quiz_samples)
        }
    
    def _parse_table_section(self, content: str, start_marker: str, end_marker: str, 
                            fields: List[str], category: str) -> List[Dict[str, Any]]:
        """Parse table-based section"""
        # Extract section
        start_idx = content.find(start_marker)
        if start_idx == -1:
            return []
        
        if end_marker:
            end_idx = content.find(end_marker, start_idx)
            section = content[start_idx:end_idx] if end_idx != -1 else content[start_idx:]
        else:
            section = content[start_idx:]
        
        # Parse table rows (format: ID | field1 | field2 | ...)
        lines = section.split('\n')
        data = []
        item_id = 1
        
        for line in lines:
            line = line.strip()
            if '|' in line and not line.startswith('필드'):
                parts = [p.strip() for p in line.split('|')]
                if len(parts) >= len(fields):
                    item = {
                        "id": item_id,
                        "category": category,
                        "content": " | ".join(parts[1:]),
                        "metadata": {}
                    }
                    
                    # Add field-specific data
                    for i, field in enumerate(fields[1:], 1):
                        if i < len(parts):
                            item["metadata"][field] = parts[i]
                    
                    data.append(item)
                    item_id += 1
        
        return data
    
    def _parse_list_section(self, content: str, start_marker: str, 
                           end_marker: str, category: str) -> List[Dict[str, Any]]:
        """Parse list-based section"""
        # Extract section
        start_idx = content.find(start_marker)
        if start_idx == -1:
            return []
        
        if end_marker:
            end_idx = content.find(end_marker, start_idx)
            section = content[start_idx:end_idx] if end_idx != -1 else content[start_idx:]
        else:
            section = content[start_idx:]
        
        # Parse list items (separated by blank lines)
        lines = section.split('\n')
        data = []
        item_id = 1
        current_item = []
        
        for line in lines:
            line = line.strip()
            if line and not line.startswith('[') and not line.startswith('필드'):
                current_item.append(line)
            elif current_item:
                content_text = " ".join(current_item)
                if content_text:
                    data.append({
                        "id": item_id,
                        "category": category,
                        "content": content_text,
                        "metadata": {}
                    })
                    item_id += 1
                current_item = []
        
        # Add last item
        if current_item:
            content_text = " ".join(current_item)
            if content_text:
                data.append({
                    "id": item_id,
                    "category": category,
                    "content": content_text,
                    "metadata": {}
                })
        
        return data
    
    def _save_json(self, filename: str, data: List[Dict[str, Any]]):
        """Save data to JSON file"""
        filepath = self.output_dir / filename
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"✓ Saved {filename}: {len(data)} items")
    
    def _append_json(self, filename: str, new_data: List[Dict[str, Any]]):
        """Append data to existing JSON file"""
        filepath = self.output_dir / filename
        
        # Load existing data
        if filepath.exists():
            with open(filepath, 'r', encoding='utf-8') as f:
                existing_data = json.load(f)
        else:
            existing_data = []
        
        # Update IDs
        max_id = max([item["id"] for item in existing_data], default=0)
        for item in new_data:
            item["id"] = max_id + item["id"]
        
        # Append and save
        existing_data.extend(new_data)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(existing_data, f, ensure_ascii=False, indent=2)
        print(f"✓ Appended to {filename}: +{len(new_data)} items (total: {len(existing_data)})")


def main():
    """Main execution"""
    print("=" * 60)
    print("TradeOnboarding Agent - Data Parser")
    print("=" * 60)
    
    # Initialize parser
    parser = DataParser(
        raw_data_dir="../dataset/raw",
        output_dir="../dataset"
    )
    
    # Parse dummydata1.md
    print("\n[1/2] Parsing dummydata1.md...")
    stats1 = parser.parse_dummydata1()
    print(f"\nDummydata1 Summary:")
    for key, count in stats1.items():
        print(f"  - {key}: {count} items")
    
    # Parse dummydata2.md
    print("\n[2/2] Parsing dummydata2.md...")
    stats2 = parser.parse_dummydata2()
    print(f"\nDummydata2 Summary:")
    for key, count in stats2.items():
        print(f"  - {key}: {count} items")
    
    print("\n" + "=" * 60)
    print("✓ Data parsing completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    main()
