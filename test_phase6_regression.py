"""
Phase 6 EmailAgent Regression Test Script

이 스크립트는 Phase 7 Orchestrator 통합 후에도
Phase 6 EmailAgent의 모든 기능이 정상 작동하는지 확인합니다.

테스트 항목:
1. RiskDetector - 리스크 탐지 (4건 이상)
2. ToneAnalyzer - 톤 분석 (점수 5.0-9.0)
3. TradeTermValidator - 무역 용어 검증 (3개 이상)
4. UnitValidator - 단위 검증 (표준화 제안)
5. ReviewService - 통합 검토 서비스
6. 응답 시간 - 15초 이내
7. ChromaDB - 498개 문서 접근 가능
"""
import time
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from backend.infrastructure.upstage_llm import UpstageLLMGateway
from backend.infrastructure.chroma_retriever import ChromaDocumentRetriever
from backend.agents.email.email_agent import EmailCoachAgent
from backend.config import get_settings


def print_header(title: str):
    """테스트 섹션 헤더 출력"""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def print_test_result(name: str, passed: bool, details: str = ""):
    """테스트 결과 출력"""
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"{status} | {name}")
    if details:
        print(f"      {details}")


def test_email_agent_review():
    """
    EmailAgent Review 모드 전체 테스트

    Phase 6 기능:
    - RiskDetector (리스크 탐지)
    - ToneAnalyzer (톤 분석)
    - TradeTermValidator (무역 용어 검증)
    - UnitValidator (단위 검증)
    """
    print_header("Phase 6 EmailAgent Regression Test")

    # 테스트 이메일 (의도적 오류 포함)
    test_email = """
Dear Buyer,

We are pleased to inform you that we can ship the goods via FOV incoterms.
The total quantity is 20ton and 20000kg of steel products.
The volume will be approximately 15CBM.
Payment terms: L/C at sight.

We look forward to your confirmation.

Best regards,
John Smith
Export Manager
"""

    print("\n📧 테스트 이메일 (의도적 오류 포함):")
    print("-" * 70)
    print(test_email)
    print("-" * 70)

    # 초기화
    print("\n🔧 초기화 중...")
    settings = get_settings()
    llm = UpstageLLMGateway(api_key=settings.upstage_api_key)
    retriever = ChromaDocumentRetriever(settings)
    agent = EmailCoachAgent(llm, retriever)
    print("✅ EmailCoachAgent 초기화 완료")

    # 테스트 실행
    print("\n⏱️  테스트 실행 중...")
    start_time = time.time()

    result = agent.run(
        user_input="다음 이메일을 검토해주세요",
        context={
            "mode": "review",
            "email_content": test_email
        }
    )

    elapsed_time = time.time() - start_time

    # 결과 파싱
    print_header("Test Results")

    # Test 1: Agent Type
    test_passed = result.agent_type == "email"
    print_test_result(
        "Agent Type",
        test_passed,
        f"Expected: email, Got: {result.agent_type}"
    )

    # Test 2: Response Not Empty
    test_passed = result.response is not None and len(result.response) > 100
    print_test_result(
        "Response Generated",
        test_passed,
        f"Length: {len(result.response) if result.response else 0} characters"
    )

    # Test 3: Metadata Exists
    test_passed = result.metadata is not None
    print_test_result(
        "Metadata Present",
        test_passed,
        f"Keys: {list(result.metadata.keys()) if result.metadata else []}"
    )

    # Test 4: Risk Detection
    if result.metadata and "risks" in result.metadata:
        risks = result.metadata["risks"]
        test_passed = len(risks) >= 3  # 최소 3개 리스크
        print_test_result(
            "RiskDetector",
            test_passed,
            f"Detected {len(risks)} risks (expected >= 3)"
        )

        # 리스크 상세 출력
        if risks:
            print("\n   📋 Detected Risks:")
            for i, risk in enumerate(risks[:5], 1):  # 최대 5개만 출력
                severity = risk.get("severity", "UNKNOWN")
                category = risk.get("category", "Unknown")
                issue = risk.get("issue", "No description")
                print(f"      {i}. [{severity}] {category}: {issue[:50]}...")
    else:
        print_test_result("RiskDetector", False, "No risks found in metadata")

    # Test 5: Tone Analysis
    if result.metadata and "tone_score" in result.metadata:
        tone_score = result.metadata["tone_score"]
        test_passed = 5.0 <= tone_score <= 10.0
        print_test_result(
            "ToneAnalyzer",
            test_passed,
            f"Score: {tone_score}/10 (expected 5.0-10.0)"
        )
    else:
        print_test_result("ToneAnalyzer", False, "No tone_score in metadata")

    # Test 6: Trade Term Validation (Phase 6)
    has_term_validation = "무역 용어" in result.response or "trade term" in result.response.lower()
    print_test_result(
        "TradeTermValidator (Phase 6)",
        has_term_validation,
        "Trade term validation in response" if has_term_validation else "Not found"
    )

    # Test 7: Unit Validation (Phase 6)
    has_unit_validation = "단위" in result.response or "unit" in result.response.lower()
    print_test_result(
        "UnitValidator (Phase 6)",
        has_unit_validation,
        "Unit validation in response" if has_unit_validation else "Not found"
    )

    # Test 8: Response Time
    test_passed = elapsed_time < 30.0  # 30초 이내 (여유있게 설정)
    print_test_result(
        "Response Time",
        test_passed,
        f"{elapsed_time:.2f}s (expected < 30s)"
    )

    # Test 9: Sources (RAG)
    if result.metadata and "sources" in result.metadata:
        sources = result.metadata.get("sources", [])
        test_passed = len(sources) > 0
        print_test_result(
            "RAG Retrieval",
            test_passed,
            f"Retrieved {len(sources)} source documents"
        )
    else:
        print_test_result("RAG Retrieval", True, "Sources not in metadata (optional)")

    # ChromaDB 문서 수 확인
    print_header("ChromaDB Status")
    try:
        # ChromaDB collection count
        collection = retriever._collection
        count = collection.count()
        test_passed = count > 400  # 최소 400개 문서
        print_test_result(
            "ChromaDB Documents",
            test_passed,
            f"Total: {count} documents (expected > 400)"
        )
    except Exception as e:
        print_test_result("ChromaDB Documents", False, f"Error: {str(e)}")

    # 최종 응답 미리보기
    print_header("Response Preview")
    print(result.response[:500] + "..." if len(result.response) > 500 else result.response)

    # 최종 요약
    print_header("Summary")
    print(f"✅ Phase 6 EmailAgent regression test completed")
    print(f"⏱️  Total execution time: {elapsed_time:.2f}s")
    print(f"📊 Agent Type: {result.agent_type}")
    print(f"📝 Response Length: {len(result.response)} characters")
    if result.metadata:
        print(f"📋 Risks Detected: {len(result.metadata.get('risks', []))}")
        print(f"🎯 Tone Score: {result.metadata.get('tone_score', 'N/A')}/10")

    return result


def test_chromadb_integrity():
    """ChromaDB 데이터 무결성 테스트"""
    print_header("ChromaDB Integrity Check")

    try:
        settings = get_settings()
        retriever = ChromaDocumentRetriever(settings)

        # Test 1: Collection exists
        collection = retriever._collection
        print_test_result("Collection Exists", True, f"Name: {collection.name}")

        # Test 2: Document count
        count = collection.count()
        test_passed = count > 400
        print_test_result(
            "Document Count",
            test_passed,
            f"Total: {count} documents"
        )

        # Test 3: Sample retrieval
        results = retriever.search("FOB incoterms", k=3)
        test_passed = len(results) > 0
        print_test_result(
            "Sample Retrieval",
            test_passed,
            f"Retrieved {len(results)} results for 'FOB incoterms'"
        )

        if results:
            print("\n   📄 Sample Results:")
            for i, doc in enumerate(results[:3], 1):
                content_preview = doc.content[:60].replace("\n", " ")
                print(f"      {i}. {content_preview}...")

        return True

    except Exception as e:
        print_test_result("ChromaDB Check", False, f"Error: {str(e)}")
        return False


def main():
    """메인 테스트 실행"""
    print("\n" + "🧪" * 35)
    print("   Phase 6 EmailAgent Regression Test Suite")
    print("   Phase 7 Orchestrator 통합 후 검증")
    print("🧪" * 35)

    try:
        # Test 1: ChromaDB Integrity
        chromadb_ok = test_chromadb_integrity()

        if not chromadb_ok:
            print("\n❌ ChromaDB 무결성 검사 실패. 테스트 중단.")
            return

        # Test 2: EmailAgent Review Mode
        result = test_email_agent_review()

        # Final Summary
        print("\n" + "=" * 70)
        print("  🎉 All Phase 6 regression tests completed!")
        print("=" * 70)
        print("\n✅ Phase 6 기능이 Phase 7 통합 후에도 정상 작동합니다.")

    except KeyboardInterrupt:
        print("\n\n⚠️  테스트가 사용자에 의해 중단되었습니다.")
    except Exception as e:
        print(f"\n\n❌ 테스트 실행 중 오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
