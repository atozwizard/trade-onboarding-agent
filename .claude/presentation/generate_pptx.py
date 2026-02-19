"""
Trade Onboarding Agent - PPTX 자동 생성 스크립트 (v3)
폰트: Noto Sans KR
실행: uv run python .claude/presentation/generate_pptx.py

슬라이드 구성 (17장):
01 표지
02 Contents
03 문제 정의
04 서비스 개요
05 Orchestrator (에이전트 라우팅 방식)
06 QuizAgent 핵심기능+UX
07 EvalTool 평가
08 QuizAgent 확장성
09 QuizAgent 데모
10 EmailAgent 핵심기능+UX
11 EmailAgent 확장성
12 EmailAgent 데모
13 RiskManagingAgent 핵심기능+UX
14 RiskManagingAgent 확장성
15 RiskManagingAgent 데모
16 기술스택 + 역할분담
17 마무리 + Q&A
"""

from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
import os

# -----------------------------------------
# 색상 팔레트
# -----------------------------------------
C_NAVY   = RGBColor(0x1A, 0x23, 0x3A)
C_BLUE   = RGBColor(0x2D, 0x6A, 0xE0)
C_LIGHT  = RGBColor(0xF4, 0xF6, 0xFB)
C_WHITE  = RGBColor(0xFF, 0xFF, 0xFF)
C_DARK   = RGBColor(0x1A, 0x1A, 0x2E)
C_GRAY   = RGBColor(0x6B, 0x7B, 0x8D)
C_GREEN  = RGBColor(0x27, 0xAE, 0x60)
C_ORANGE = RGBColor(0xE6, 0x7E, 0x22)
C_RED    = RGBColor(0xC0, 0x39, 0x2B)
C_PURPLE = RGBColor(0x6C, 0x3D, 0xA8)

FONT = "Noto Sans KR"
OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "TradeOnboardingAgent_v3_updated.pptx")


# -----------------------------------------
# 헬퍼
# -----------------------------------------

def new_prs():
    prs = Presentation()
    prs.slide_width  = Inches(13.33)
    prs.slide_height = Inches(7.5)
    return prs


def blank_slide(prs, bg_color=None):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    if bg_color:
        fill = slide.background.fill
        fill.solid()
        fill.fore_color.rgb = bg_color
    return slide


def add_rect(slide, x, y, w, h, color, line=False):
    shape = slide.shapes.add_shape(1, Inches(x), Inches(y), Inches(w), Inches(h))
    shape.fill.solid()
    shape.fill.fore_color.rgb = color
    if not line:
        shape.line.fill.background()
    return shape


def add_text(slide, text, x, y, w, h,
             size=16, bold=False, color=C_DARK,
             align=PP_ALIGN.LEFT, wrap=True):
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = wrap
    p = tf.paragraphs[0]
    p.alignment = align
    run = p.add_run()
    run.text = text
    run.font.name = FONT
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.color.rgb = color
    return tb


def add_lines(slide, lines, x, y, w, h,
              size=16, bold=False, color=C_DARK,
              align=PP_ALIGN.LEFT):
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = True
    for i, line in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        run = p.add_run()
        run.text = line
        run.font.name = FONT
        run.font.size = Pt(size)
        run.font.bold = bold
        run.font.color.rgb = color
    return tb


def header_bar(slide, title, section_label=None):
    add_rect(slide, 0, 0, 13.33, 1.0, C_NAVY)
    add_text(slide, title, 0.4, 0.18, 10.0, 0.65,
             size=20, bold=True, color=C_WHITE)
    if section_label:
        add_text(slide, section_label, 10.5, 0.25, 2.6, 0.5,
                 size=12, color=RGBColor(0xAA, 0xBB, 0xCC),
                 align=PP_ALIGN.RIGHT)


def bottom_bar(slide):
    add_rect(slide, 0, 7.15, 13.33, 0.35, C_BLUE)
    add_text(slide, "Trade Onboarding Agent   |   SeSAC AIPE Project",
             0, 7.2, 13.33, 0.28, size=9, color=C_WHITE, align=PP_ALIGN.CENTER)


def img_placeholder(slide, x, y, w, h, label=""):
    add_rect(slide, x, y, w, h, RGBColor(0xDD, 0xE8, 0xFF))
    if label:
        add_text(slide, label, x + 0.1, y + h/2 - 0.3, w - 0.2, 0.7,
                 size=11, color=C_GRAY, align=PP_ALIGN.CENTER)


def demo_placeholder(slide, x, y, w, h, label=""):
    """데모 스크린샷 플레이스홀더 (진한 배경)"""
    add_rect(slide, x, y, w, h, RGBColor(0x22, 0x2C, 0x45))
    add_rect(slide, x + 0.05, y + 0.05, w - 0.1, 0.35, RGBColor(0x3A, 0x4A, 0x6B))
    add_text(slide, "DEMO", x + 0.1, y + 0.1, 0.9, 0.25,
             size=10, bold=True, color=RGBColor(0xAA, 0xBB, 0xFF))
    if label:
        add_text(slide, label, x + 0.15, y + 0.6, w - 0.3, h - 0.8,
                 size=11, color=RGBColor(0xCC, 0xDD, 0xFF), align=PP_ALIGN.CENTER)


# -----------------------------------------
# SLIDE 01: 표지
# -----------------------------------------
def s01_cover(prs):
    slide = blank_slide(prs, C_NAVY)
    add_rect(slide, 0, 0, 13.33, 0.12, C_BLUE)
    add_text(slide, "Trade Onboarding Agent",
             1.0, 1.6, 11.3, 1.3, size=40, bold=True,
             color=C_WHITE, align=PP_ALIGN.CENTER)
    add_text(slide, "채팅으로 시작하는 무역 실무 온보딩",
             1.0, 2.9, 11.3, 0.8, size=22,
             color=RGBColor(0xAA, 0xCC, 0xFF), align=PP_ALIGN.CENTER)
    add_text(slide, "이성준  ·  차세종  ·  황지은  ·  이영기",
             1.0, 3.9, 11.3, 0.5, size=16,
             color=RGBColor(0xCC, 0xDD, 0xEE), align=PP_ALIGN.CENTER)
    add_text(slide, "발표자: 이성준",
             1.0, 4.4, 11.3, 0.4, size=14,
             color=RGBColor(0xAA, 0xBB, 0xCC), align=PP_ALIGN.CENTER)
    add_text(slide, "[ 배경 이미지: 항구/컨테이너 삽입 권장 ]",
             1.0, 5.3, 11.3, 0.4, size=11,
             color=RGBColor(0x55, 0x66, 0x77), align=PP_ALIGN.CENTER)
    add_rect(slide, 0, 7.1, 13.33, 0.4, C_BLUE)
    add_text(slide, "2026  |  SeSAC AIPE Project",
             0, 7.18, 13.33, 0.3, size=10, color=C_WHITE, align=PP_ALIGN.CENTER)


# -----------------------------------------
# SLIDE 02: Contents
# -----------------------------------------
def s02_contents(prs):
    slide = blank_slide(prs, C_LIGHT)
    header_bar(slide, "Contents")
    bottom_bar(slide)

    items = [
        ("01", "서비스 기획 — 문제 정의 · 서비스 개요", C_BLUE),
        ("02", "Agent 설계 — Orchestrator · RAG · Tool", C_PURPLE),
        ("03", "Agent 개발 — Quiz / Email / Risk",
         C_GREEN),
        ("04", "시연 — 기능별 데모 · 기술스택 · 마무리", C_ORANGE),
    ]
    sub = [
        "",
        "",
        "QuizAgent(EvalTool)  /  EmailAgent  /  RiskManagingAgent",
        "",
    ]

    for i, ((num, title, color), desc) in enumerate(zip(items, sub)):
        y = 1.2 + i * 1.3
        add_rect(slide, 0.8, y, 0.7, 0.9, color)
        add_text(slide, num, 0.8, y + 0.15, 0.7, 0.6,
                 size=18, bold=True, color=C_WHITE, align=PP_ALIGN.CENTER)
        add_rect(slide, 1.5, y, 11.3, 0.9, RGBColor(0xEE, 0xF2, 0xFF))
        add_text(slide, title, 1.65, y + 0.1, 9.0, 0.5,
                 size=17, bold=True, color=C_DARK)
        if desc:
            add_text(slide, desc, 1.65, y + 0.52, 9.0, 0.35,
                     size=12, color=C_GRAY)


# -----------------------------------------
# SLIDE 03: 문제 정의
# -----------------------------------------
def s03_problem(prs):
    slide = blank_slide(prs, C_LIGHT)
    header_bar(slide, "왜 무역 신입사원 온보딩이 어려운가?", "01. 서비스 기획")
    bottom_bar(slide)

    lines = [
        "● 무역 실무 용어·프로세스는 암기보다 반복 경험이 필요",
        "● 기존 온보딩: 문서 중심  →  단방향 학습  →  낮은 몰입도",
        "● 실수 한 번이 페널티·클레임·계약 분쟁으로 직결되는 고위험 도메인",
        "● AI 코치가 대화하며 실시간 피드백을 주는 시스템 부재",
    ]
    add_lines(slide, lines, 1.0, 1.3, 11.3, 3.0, size=17, color=C_DARK)

    add_rect(slide, 1.0, 4.7, 11.3, 1.1, C_NAVY)
    add_text(slide, '"실무는 교과서가 아니라 대화로 배운다"',
             1.2, 4.88, 11.0, 0.75, size=22, bold=True,
             color=C_WHITE, align=PP_ALIGN.CENTER)

    add_text(slide, "[ 이미지: 문서 더미 vs 채팅 버블 Before/After 삽입 권장 ]",
             1.0, 6.0, 11.3, 0.4, size=10, color=C_GRAY)


# -----------------------------------------
# SLIDE 04: 서비스 개요
# -----------------------------------------
def s04_overview(prs):
    slide = blank_slide(prs, C_LIGHT)
    header_bar(slide, "서비스 개요 및 전체 흐름", "01. 서비스 기획")
    bottom_bar(slide)

    lines = [
        "● 타겟: 무역회사 신입사원 (1~2년차)",
        "",
        "● 핵심 학습 영역",
        "    ○ Incoterms / 결제 조건 (L/C, T/T)",
        "    ○ 무역 이메일 작성 및 검토",
        "    ○ 공급망 리스크 대응",
        "",
        "● 데이터 규모",
        "    ○ 17개 JSON  /  782 ingestable records",
        "    ○ ICC 무역용어집 284개 포함",
    ]
    add_lines(slide, lines, 0.9, 1.2, 6.0, 5.5, size=14, color=C_DARK)

    img_placeholder(slide, 7.2, 1.2, 5.9, 5.5,
                    "[ 기획서 시스템 개요\ngraph LR 다이어그램\n캡처 이미지 삽입 ]")


# -----------------------------------------
# SLIDE 05: Orchestrator — 에이전트 라우팅 방식
# -----------------------------------------
def s05_orchestrator(prs):
    slide = blank_slide(prs, C_LIGHT)
    header_bar(slide, "Orchestrator — 에이전트 라우팅 방식",
               "02. Agent 설계")
    bottom_bar(slide)

    # 왼쪽: LLM 인텐트 분류 기반 라우팅 흐름
    lines_l = [
        "● LLM 기반 인텐트 분류 (solar-pro2)",
        "",
        "    사용자 입력",
        "         |",
        "    [LLM 인텐트 분류]",
        "         |",
        "    퀴즈 관련 키워드   -->  QuizAgent",
        "    이메일 관련 키워드 -->  EmailAgent",
        "    리스크 관련 키워드 -->  RiskManagingAgent",
        "    그 외             -->  DefaultChatAgent",
    ]
    add_lines(slide, lines_l, 0.9, 1.2, 6.1, 5.8, size=13, color=C_DARK)

    # 구분선
    add_rect(slide, 7.1, 1.1, 0.06, 5.8, C_BLUE)

    # 오른쪽: 라우팅 우선순위 + RAG 필요 이유
    lines_r = [
        "● 라우팅 우선순위",
        "    ① active_agent 유지",
        "        (멀티턴 진행 중일 때 최우선)",
        "    ② context.mode 명시",
        "        (프론트엔드 오버라이드)",
        "    ③ LLM 인텐트 분류",
        "    ④ DefaultChatAgent (폴백)",
        "",
        "● 왜 에이전트로 분리하나?",
        "    ○ 무역 도메인 특화 지식 → RAG 필요",
        "    ○ 퀴즈 품질 보장 → EvalTool 루프",
        "    ○ 리스크 분석 → 멀티턴 + 보고서",
    ]
    add_lines(slide, lines_r, 7.3, 1.2, 5.8, 5.8, size=13, color=C_DARK)


# -----------------------------------------
# SLIDE 06: QuizAgent 핵심기능 + UX
# -----------------------------------------
def s06_quiz(prs):
    slide = blank_slide(prs, C_LIGHT)
    add_rect(slide, 0, 0, 13.33, 1.0, C_GREEN)
    add_text(slide, "QuizAgent — RAG 기반 퀴즈 학습",
             0.4, 0.18, 10.0, 0.65, size=20, bold=True, color=C_WHITE)
    add_text(slide, "03. Agent 개발",
             10.5, 0.25, 2.6, 0.5, size=12,
             color=RGBColor(0xCC, 0xFF, 0xCC), align=PP_ALIGN.RIGHT)
    bottom_bar(slide)

    lines_l = [
        "● 핵심 기능",
        "    ○ ChromaDB에서 실제 무역 용어 검색",
        "        → 4지선다 5문제 생성",
        "    ○ 출제 방향: 용어->설명 / 설명->용어 (양방향)",
        "    ○ 난이도: easy / medium / hard / 혼합(기본값)",
        "    ○ EvalTool: 5항목 품질 자동 검증",
        "    ○ 불합격 시 최대 2회 재시도",
        "        → 다른 용어로 대체 생성",
        "    ○ 정답 해설은 답 제출 후에만 공개",
    ]
    lines_r = [
        "● 목표 UX",
        '    ○ "FOB 퀴즈 풀고 싶어요"',
        "        한 문장으로 즉시 시작",
        "    ○ 번호 입력만으로 답변",
        "        → 정오답 + 해설 즉시 제공",
        "    ○ RAG 유사 용어를 오답으로 배치",
        "        → 학습 밀도 향상",
        "    ○ 혼동하기 쉬운 용어끼리",
        "        비교하는 구조",
    ]
    add_lines(slide, lines_l, 0.9, 1.1, 6.1, 5.8, size=13, color=C_DARK)
    add_rect(slide, 7.1, 1.1, 0.06, 5.8, C_GREEN)
    add_lines(slide, lines_r, 7.3, 1.1, 5.8, 5.8, size=13, color=C_DARK)


# -----------------------------------------
# SLIDE 07: EvalTool 평가
# -----------------------------------------
def s07_evaltool(prs):
    slide = blank_slide(prs, C_LIGHT)
    add_rect(slide, 0, 0, 13.33, 1.0, C_GREEN)
    add_text(slide, "EvalTool — 퀴즈 품질 자동 검증",
             0.4, 0.18, 10.0, 0.65, size=20, bold=True, color=C_WHITE)
    add_text(slide, "03. Agent 개발",
             10.5, 0.25, 2.6, 0.5, size=12,
             color=RGBColor(0xCC, 0xFF, 0xCC), align=PP_ALIGN.RIGHT)
    bottom_bar(slide)

    # 검증 항목 (왼쪽)
    lines_l = [
        "● EvalTool 검증 항목 (5개)",
        "",
        "    1. 문제(question)",
        "        RAG 원본 내용 반영 여부",
        "    2. 정답 선택지",
        "        원본 데이터 일치 여부",
        "    3. 오답 선택지",
        "        실존 용어 기반 여부 (허구 배제)",
        "    4. 정답 인덱스",
        "        RAG 재검색으로 재확인",
        "    5. 해설",
        "        원본 내용 부합 여부",
    ]
    add_lines(slide, lines_l, 0.9, 1.1, 5.8, 5.8, size=13, color=C_DARK)

    add_rect(slide, 7.1, 1.1, 0.06, 5.8, C_GREEN)

    # 재시도 루프 (오른쪽)
    lines_r = [
        "● 재시도 및 대체 생성 루프",
        "    MAX_RETRY = 2",
        "",
        "    is_valid = false",
        "         |",
        "    issues 피드백 포함 재생성",
        "         |",
        "    2회 소진 시 다른 용어로 대체",
        "         |",
        "    합격 5문제 달성 시 즉시 종료",
        "",
        "● 예상 품질 지표",
        "    퀴즈 합격률    ~90%",
        "    무역 용어 검증 ~90%",
        "    단위 검증      ~95%",
    ]
    add_lines(slide, lines_r, 7.3, 1.1, 5.8, 5.8, size=13, color=C_DARK)


# -----------------------------------------
# SLIDE 08: QuizAgent 확장성
# -----------------------------------------
def s08_quiz_ext(prs):
    slide = blank_slide(prs, C_LIGHT)
    add_rect(slide, 0, 0, 13.33, 1.0, C_GREEN)
    add_text(slide, "QuizAgent — 확장 가능성",
             0.4, 0.18, 10.0, 0.65, size=20, bold=True, color=C_WHITE)
    add_text(slide, "03. Agent 개발",
             10.5, 0.25, 2.6, 0.5, size=12,
             color=RGBColor(0xCC, 0xFF, 0xCC), align=PP_ALIGN.RIGHT)
    bottom_bar(slide)

    # 카드 1: 개인화 학습 이력
    add_rect(slide, 0.9, 1.2, 5.6, 5.5, RGBColor(0xE8, 0xF8, 0xEE))
    add_rect(slide, 0.9, 1.2, 5.6, 0.55, C_GREEN)
    add_text(slide, "개인화 학습 이력",
             0.9, 1.25, 5.6, 0.45, size=15, bold=True,
             color=C_WHITE, align=PP_ALIGN.CENTER)
    lines1 = [
        "● 회원 DB 구축",
        "    -> 개인별 오답 히스토리 저장",
        "● 오답 문제만 모아 복습 모드 자동 생성",
        "● 주제별 누적 점수",
        "    -> 취약 영역 자동 파악 및 집중 출제",
    ]
    add_lines(slide, lines1, 1.0, 2.0, 5.3, 4.3, size=14, color=C_DARK)

    # 카드 2: HR 인증 시스템
    add_rect(slide, 6.8, 1.2, 6.0, 5.5, RGBColor(0xE8, 0xF8, 0xEE))
    add_rect(slide, 6.8, 1.2, 6.0, 0.55, C_GREEN)
    add_text(slide, "HR 인증 시스템",
             6.8, 1.25, 6.0, 0.45, size=15, bold=True,
             color=C_WHITE, align=PP_ALIGN.CENTER)
    lines2 = [
        "● 사내 HR 기준(점수·주제) 충족 시",
        "    주제별 수료증 자동 발급",
        "● 인증 예시",
        "    ○ Incoterms 인증",
        "    ○ 결제 조건 인증",
        "    ○ 리스크 관리 인증",
        "● 신입 온보딩 완료 지표로 활용 가능",
    ]
    add_lines(slide, lines2, 6.95, 2.0, 5.7, 4.3, size=14, color=C_DARK)


# -----------------------------------------
# SLIDE 09: QuizAgent 데모
# -----------------------------------------
def s09_quiz_demo(prs):
    slide = blank_slide(prs, RGBColor(0x0F, 0x17, 0x2A))
    add_rect(slide, 0, 0, 13.33, 1.0, C_GREEN)
    add_text(slide, "QuizAgent 데모",
             0.4, 0.18, 10.0, 0.65, size=20, bold=True, color=C_WHITE)
    add_text(slide, "03. Agent 개발",
             10.5, 0.25, 2.6, 0.5, size=12,
             color=RGBColor(0xCC, 0xFF, 0xCC), align=PP_ALIGN.RIGHT)
    bottom_bar(slide)

    # 왼쪽: 퀴즈 생성 화면
    demo_placeholder(slide, 0.6, 1.1, 5.8, 4.5,
                     "[ 스크린샷: 퀴즈 5문제 생성 화면 ]\n\n"
                     "FOB 관련 4지선다\n난이도 easy 5문제")

    # 오른쪽: 채점 결과 화면
    demo_placeholder(slide, 6.8, 1.1, 5.8, 4.5,
                     "[ 스크린샷: 채점 결과 화면 ]\n\n"
                     "정오답 표시 + 해설 공개\n오답 기반 추가 학습 안내")

    # 하단 설명
    add_rect(slide, 0.6, 5.8, 11.8, 0.9, RGBColor(0x1A, 0x28, 0x45))
    add_text(slide, "실제 ChromaDB 검색 데이터 기반 문제 생성  |  EvalTool 자동 품질 검증 통과 후 출제",
             0.8, 5.95, 11.5, 0.6, size=13,
             color=RGBColor(0xCC, 0xFF, 0xCC), align=PP_ALIGN.CENTER)


# -----------------------------------------
# SLIDE 10: EmailAgent 핵심기능 + UX
# -----------------------------------------
def s10_email(prs):
    slide = blank_slide(prs, C_LIGHT)
    add_rect(slide, 0, 0, 13.33, 1.0, C_ORANGE)
    add_text(slide, "EmailAgent — 초안 작성부터 검토까지 한 흐름",
             0.4, 0.18, 10.0, 0.65, size=20, bold=True, color=C_WHITE)
    add_text(slide, "03. Agent 개발",
             10.5, 0.25, 2.6, 0.5, size=12,
             color=RGBColor(0xFF, 0xEE, 0xCC), align=PP_ALIGN.RIGHT)
    bottom_bar(slide)

    lines_l = [
        "● 핵심 기능",
        '    ○ Draft: "미국 바이어 제안 메일 작성"',
        "        거래 조건 반영 초안 즉시 생성",
        '    ○ 수정: "영어로 더 공손하게 바꿔줘"',
        "        같은 맥락에서 즉시 반영",
        "    ○ Review: 리스크·톤·무역용어·단위 동시 검증",
        "    ○ 예외: 본문 없을 시 추가 정보 먼저 요청",
        "        (오검토 방지)",
    ]
    lines_r = [
        "● 목표 UX",
        "    ○ 짧은 자연어 한 줄로 전체 흐름 처리",
        "    ○ FOV->FOB 오류 자동 탐지 및 교정",
        "    ○ 무역 용어·단위 오류 즉시 피드백",
        "",
        "● Review 7개 서비스 (병렬 실행)",
        "    RiskDetector / ToneAnalyzer",
        "    TradeTermValidator / UnitValidator",
        "    ResponseFormatter / DraftService",
        "    ReviewService (통합 오케스트레이션)",
    ]
    add_lines(slide, lines_l, 0.9, 1.1, 6.1, 5.8, size=13, color=C_DARK)
    add_rect(slide, 7.1, 1.1, 0.06, 5.8, C_ORANGE)
    add_lines(slide, lines_r, 7.3, 1.1, 5.8, 5.8, size=13, color=C_DARK)


# -----------------------------------------
# SLIDE 11: EmailAgent 확장성
# -----------------------------------------
def s11_email_ext(prs):
    slide = blank_slide(prs, C_LIGHT)
    add_rect(slide, 0, 0, 13.33, 1.0, C_ORANGE)
    add_text(slide, "EmailAgent — 확장 가능성",
             0.4, 0.18, 10.0, 0.65, size=20, bold=True, color=C_WHITE)
    add_text(slide, "03. Agent 개발",
             10.5, 0.25, 2.6, 0.5, size=12,
             color=RGBColor(0xFF, 0xEE, 0xCC), align=PP_ALIGN.RIGHT)
    bottom_bar(slide)

    # 카드 1: Gmail MCP 연결
    add_rect(slide, 0.9, 1.2, 5.6, 5.5, RGBColor(0xFF, 0xF5, 0xE8))
    add_rect(slide, 0.9, 1.2, 5.6, 0.55, C_ORANGE)
    add_text(slide, "Gmail MCP 연결",
             0.9, 1.25, 5.6, 0.45, size=15, bold=True,
             color=C_WHITE, align=PP_ALIGN.CENTER)
    lines1 = [
        "● Gmail MCP 서버 연동",
        "    -> 검토 완료 후 실제 발송까지 연결",
        "● 초안 작성 -> 검토 -> 발송",
        "    원스톱 이메일 워크플로우",
        "● 발송 이력 자동 저장",
        "    -> 거래처별 커뮤니케이션 관리",
    ]
    add_lines(slide, lines1, 1.0, 2.0, 5.3, 4.3, size=14, color=C_DARK)

    # 카드 2: 이메일 히스토리 학습
    add_rect(slide, 6.8, 1.2, 6.0, 5.5, RGBColor(0xFF, 0xF5, 0xE8))
    add_rect(slide, 6.8, 1.2, 6.0, 0.55, C_ORANGE)
    add_text(slide, "거래처별 이메일 히스토리",
             6.8, 1.25, 6.0, 0.45, size=15, bold=True,
             color=C_WHITE, align=PP_ALIGN.CENTER)
    lines2 = [
        "● 거래처별 이메일 히스토리 저장",
        "    -> 문체·협상 패턴 누적 학습",
        "● 과거 성공 사례 기반 초안 생성",
        "● 거래처 선호도 자동 반영",
        "    (격식체/비격식체, 국가별 문화)",
        "● 계약 이력 연계",
        "    -> 맥락에 맞는 이메일 자동 완성",
    ]
    add_lines(slide, lines2, 6.95, 2.0, 5.7, 4.3, size=14, color=C_DARK)


# -----------------------------------------
# SLIDE 12: EmailAgent 데모
# -----------------------------------------
def s12_email_demo(prs):
    slide = blank_slide(prs, RGBColor(0x1A, 0x10, 0x05))
    add_rect(slide, 0, 0, 13.33, 1.0, C_ORANGE)
    add_text(slide, "EmailAgent 데모",
             0.4, 0.18, 10.0, 0.65, size=20, bold=True, color=C_WHITE)
    add_text(slide, "03. Agent 개발",
             10.5, 0.25, 2.6, 0.5, size=12,
             color=RGBColor(0xFF, 0xEE, 0xCC), align=PP_ALIGN.RIGHT)
    bottom_bar(slide)

    # 왼쪽: 오류 탐지 화면
    demo_placeholder(slide, 0.6, 1.1, 5.8, 4.5,
                     "[ 스크린샷: FOV->FOB 오류 탐지 화면 ]\n\n"
                     "무역 용어 오류 자동 감지\n수정 제안 표시")

    # 오른쪽: 검토 결과 화면
    demo_placeholder(slide, 6.8, 1.1, 5.8, 4.5,
                     "[ 스크린샷: 이메일 검토 결과 화면 ]\n\n"
                     "리스크·톤·용어·단위 4항목\n마크다운 포맷 출력")

    # 하단 설명
    add_rect(slide, 0.6, 5.8, 11.8, 0.9, RGBColor(0x2A, 0x18, 0x05))
    add_text(slide, "FOV -> FOB 오류 자동 탐지  |  TradeTermValidator + UnitValidator 동시 검증",
             0.8, 5.95, 11.5, 0.6, size=13,
             color=RGBColor(0xFF, 0xDD, 0xAA), align=PP_ALIGN.CENTER)


# -----------------------------------------
# SLIDE 13: RiskManagingAgent 핵심기능 + UX
# -----------------------------------------
def s13_risk(prs):
    slide = blank_slide(prs, C_LIGHT)
    add_rect(slide, 0, 0, 13.33, 1.0, C_RED)
    add_text(slide, "RiskManagingAgent — 실무 선배처럼 리스크를 분석한다",
             0.4, 0.18, 10.0, 0.65, size=19, bold=True, color=C_WHITE)
    add_text(slide, "03. Agent 개발",
             10.5, 0.25, 2.6, 0.5, size=12,
             color=RGBColor(0xFF, 0xCC, 0xCC), align=PP_ALIGN.RIGHT)
    bottom_bar(slide)

    lines_l = [
        "● 핵심 기능",
        '    ○ "선적 지연" 감지 -> 상황 파악 모드 전환',
        "    ○ 협업형 멀티턴: 계약금·패널티 등",
        "        부족한 정보를 역으로 질문하며 수집",
        "    ○ 교육적 페르소나: 리스크 산출 기준",
        "        (영향도 x 발생가능성) 친절히 설명",
        "    ○ RAG 유사 클레임 사례 검색",
        "    ○ JSON 보고서: 리스크 점수 +",
        "        단기/장기 예방 전략 구조화 출력",
    ]
    lines_r = [
        "● 목표 UX",
        "    ○ 한 마디로 시작",
        "        -> 대화로 채움 -> 보고서",
        "    ○ '자동 응답기'가 아닌",
        "        '실무 선배' 역할",
        "",
        "● 멀티턴 상태 관리",
        "    analysis_in_progress = True",
        "    정보 수집 완료 ->",
        "    JSON RiskReport 자동 생성",
        "    analysis_in_progress = False",
    ]
    add_lines(slide, lines_l, 0.9, 1.1, 6.1, 5.8, size=12, color=C_DARK)
    add_rect(slide, 7.1, 1.1, 0.06, 5.8, C_RED)
    add_lines(slide, lines_r, 7.3, 1.1, 5.8, 5.8, size=12, color=C_DARK)


# -----------------------------------------
# SLIDE 14: RiskManagingAgent 확장성
# -----------------------------------------
def s14_risk_ext(prs):
    slide = blank_slide(prs, C_LIGHT)
    add_rect(slide, 0, 0, 13.33, 1.0, C_RED)
    add_text(slide, "RiskManagingAgent — 확장 가능성",
             0.4, 0.18, 10.0, 0.65, size=20, bold=True, color=C_WHITE)
    add_text(slide, "03. Agent 개발",
             10.5, 0.25, 2.6, 0.5, size=12,
             color=RGBColor(0xFF, 0xCC, 0xCC), align=PP_ALIGN.RIGHT)
    bottom_bar(slide)

    # 카드 1: 실시간 글로벌 리스크 감지
    add_rect(slide, 0.9, 1.2, 5.6, 5.5, RGBColor(0xFF, 0xEE, 0xEE))
    add_rect(slide, 0.9, 1.2, 5.6, 0.55, C_RED)
    add_text(slide, "실시간 글로벌 리스크 감지",
             0.9, 1.25, 5.6, 0.45, size=14, bold=True,
             color=C_WHITE, align=PP_ALIGN.CENTER)
    lines1 = [
        "● 해외 뉴스 API 연동",
        "    -> 실시간 무역 리스크 감지",
        "● 항만 혼잡도·선박 위치 데이터 연동",
        "● 대화 없이도 선제적 경고 트리거",
        "    -> 발생 전에 미리 알림",
        "● 국가별 리스크 인덱스 자동 업데이트",
    ]
    add_lines(slide, lines1, 1.0, 2.0, 5.3, 4.3, size=14, color=C_DARK)

    # 카드 2: 사내 ERP 연동
    add_rect(slide, 6.8, 1.2, 6.0, 5.5, RGBColor(0xFF, 0xEE, 0xEE))
    add_rect(slide, 6.8, 1.2, 6.0, 0.55, C_RED)
    add_text(slide, "사내 ERP 연동",
             6.8, 1.25, 6.0, 0.45, size=15, bold=True,
             color=C_WHITE, align=PP_ALIGN.CENTER)
    lines2 = [
        "● 계약 금액·페널티 조항 자동 조회",
        "    -> 사용자 입력 불필요",
        "● 정확도 향상",
        "    (실제 계약 데이터 기반 분석)",
        "● 과거 리스크 이력 누적",
        "    -> 유사 상황 패턴 학습",
        "● 리스크 보고서 -> ERP 자동 등록",
    ]
    add_lines(slide, lines2, 6.95, 2.0, 5.7, 4.3, size=14, color=C_DARK)


# -----------------------------------------
# SLIDE 15: RiskManagingAgent 데모
# -----------------------------------------
def s15_risk_demo(prs):
    slide = blank_slide(prs, RGBColor(0x1A, 0x05, 0x05))
    add_rect(slide, 0, 0, 13.33, 1.0, C_RED)
    add_text(slide, "RiskManagingAgent 데모",
             0.4, 0.18, 10.0, 0.65, size=20, bold=True, color=C_WHITE)
    add_text(slide, "03. Agent 개발",
             10.5, 0.25, 2.6, 0.5, size=12,
             color=RGBColor(0xFF, 0xCC, 0xCC), align=PP_ALIGN.RIGHT)
    bottom_bar(slide)

    # 왼쪽: 멀티턴 대화 화면
    demo_placeholder(slide, 0.6, 1.1, 5.8, 4.5,
                     "[ 스크린샷: 멀티턴 대화 화면 ]\n\n"
                     '"선적 지연" 입력\n-> 추가 정보 질문\n-> 분석 완료')

    # 오른쪽: JSON 보고서 시각화
    demo_placeholder(slide, 6.8, 1.1, 5.8, 4.5,
                     "[ 스크린샷: JSON 보고서 시각화 ]\n\n"
                     "리스크 점수 색상 코딩\ncritical / high / medium\n단기·장기 예방 전략")

    # 하단 설명
    add_rect(slide, 0.6, 5.8, 11.8, 0.9, RGBColor(0x2A, 0x08, 0x08))
    add_text(slide, "멀티턴 대화로 정보 수집  |  RAG 유사 클레임 사례 검색  |  JSON 구조화 보고서 출력",
             0.8, 5.95, 11.5, 0.6, size=13,
             color=RGBColor(0xFF, 0xCC, 0xCC), align=PP_ALIGN.CENTER)


# -----------------------------------------
# SLIDE 16: 기술 스택 + 역할 분담
# -----------------------------------------
def s16_stack(prs):
    slide = blank_slide(prs, C_LIGHT)
    header_bar(slide, "기술 스택 및 역할 분담",
               "04. 시연")
    bottom_bar(slide)

    headers = ["레이어", "기술", "역할"]
    rows = [
        ["패키지 관리", "uv", "Python 패키지 매니저"],
        ["프론트엔드",  "React 18 + Vite 5", "채팅 UI"],
        ["백엔드",      "FastAPI + Python 3.11", "RESTful API 서버"],
        ["LLM",        "Upstage Solar (solar-pro2)", "자연어 이해/생성"],
        ["임베딩",      "Upstage Solar Embedding", "문서 벡터화 (1024차원)"],
        ["벡터 DB",    "ChromaDB", "RAG 문서 검색 (cosine)"],
        ["트레이싱",    "LangSmith", "에이전트 실행 디버깅"],
    ]
    col_w = [2.2, 3.4, 3.0]
    col_x = [0.9, 3.1, 6.5]
    y0 = 1.2

    add_rect(slide, 0.9, y0, 8.7, 0.44, C_NAVY)
    for ci, (h, cx, cw) in enumerate(zip(headers, col_x, col_w)):
        add_text(slide, h, cx + 0.05, y0 + 0.06, cw, 0.34,
                 size=12, bold=True, color=C_WHITE)

    for ri, row in enumerate(rows):
        bg = RGBColor(0xEE, 0xF2, 0xFF) if ri % 2 == 0 else C_WHITE
        add_rect(slide, 0.9, y0 + 0.44 + ri * 0.42, 8.7, 0.42, bg)
        for ci, (cell, cx, cw) in enumerate(zip(row, col_x, col_w)):
            add_text(slide, cell, cx + 0.05, y0 + 0.47 + ri * 0.42,
                     cw, 0.38, size=11, color=C_DARK)

    # 역할 분담
    roles = [
        ("이성준", "QuizAgent · EvalTool", C_GREEN),
        ("차세종", "RiskManagingAgent", C_RED),
        ("황지은", "EmailAgent", C_ORANGE),
        ("이영기", "프론트엔드 · RAG", C_BLUE),
    ]
    add_rect(slide, 9.8, y0, 3.3, 0.44, C_NAVY)
    add_text(slide, "역할 분담", 9.85, y0 + 0.06, 3.2, 0.34,
             size=13, bold=True, color=C_WHITE, align=PP_ALIGN.CENTER)
    for i, (name, role, color) in enumerate(roles):
        add_rect(slide, 9.8, y0 + 0.44 + i * 1.0, 3.3, 0.95, color)
        add_text(slide, name, 9.85, y0 + 0.5 + i * 1.0, 3.2, 0.4,
                 size=14, bold=True, color=C_WHITE, align=PP_ALIGN.CENTER)
        add_text(slide, role, 9.85, y0 + 0.88 + i * 1.0, 3.2, 0.4,
                 size=11, color=C_WHITE, align=PP_ALIGN.CENTER)


# -----------------------------------------
# SLIDE 17: 마무리 + Q&A
# -----------------------------------------
def s17_closing(prs):
    slide = blank_slide(prs, C_LIGHT)
    header_bar(slide, "결론 및 향후 발전 방향",
               "04. 시연")
    bottom_bar(slide)

    lines_l = [
        "● 구현 성과",
        "    ○ RAG 기반 3개 전문 에이전트 완성",
        "    ○ EvalTool 자동 품질 검증 루프 구현",
        "    ○ 멀티턴 리스크 분석 + JSON 보고서",
        "    ○ 782개 무역 지식 ChromaDB 구축",
    ]
    lines_r = [
        "● 향후 발전 방향",
        "    ○ 개인별 오답 히스토리 + HR 인증 시스템",
        "    ○ Gmail MCP -> 이메일 실제 발송",
        "    ○ 실시간 리스크 감지 (뉴스 API)",
        "    ○ 사내 ERP 연동 -> 계약 정보 자동 조회",
        "    ○ Redis 세션 영속성 + PDF 계약서 분석",
    ]
    add_lines(slide, lines_l, 0.9, 1.2, 5.8, 3.5, size=14, color=C_DARK)
    add_rect(slide, 6.7, 1.2, 0.06, 3.5, C_BLUE)
    add_lines(slide, lines_r, 6.9, 1.2, 6.0, 3.5, size=14, color=C_DARK)

    add_rect(slide, 0.9, 4.9, 11.5, 1.8, C_NAVY)
    add_text(slide, "Q & A   |   감사합니다.",
             0.9, 5.25, 11.5, 1.0, size=30, bold=True,
             color=C_WHITE, align=PP_ALIGN.CENTER)


# -----------------------------------------
# MAIN
# -----------------------------------------
def main():
    prs = new_prs()
    print("Generating slides (v3 - 17 slides)...")

    s01_cover(prs)       # 01. 표지
    s02_contents(prs)    # 02. Contents
    s03_problem(prs)     # 03. 문제 정의
    s04_overview(prs)    # 04. 서비스 개요
    s05_orchestrator(prs)  # 05. Orchestrator 라우팅 방식
    s06_quiz(prs)        # 06. QuizAgent 핵심기능+UX
    s07_evaltool(prs)    # 07. EvalTool 평가
    s08_quiz_ext(prs)    # 08. QuizAgent 확장성
    s09_quiz_demo(prs)   # 09. QuizAgent 데모 (NEW)
    s10_email(prs)       # 10. EmailAgent 핵심기능+UX
    s11_email_ext(prs)   # 11. EmailAgent 확장성 (NEW)
    s12_email_demo(prs)  # 12. EmailAgent 데모 (NEW)
    s13_risk(prs)        # 13. RiskManagingAgent 핵심기능+UX
    s14_risk_ext(prs)    # 14. RiskManagingAgent 확장성 (NEW)
    s15_risk_demo(prs)   # 15. RiskManagingAgent 데모 (NEW)
    s16_stack(prs)       # 16. 기술스택 + 역할분담
    s17_closing(prs)     # 17. 마무리 + Q&A

    prs.save(OUTPUT_PATH)
    print("Done: " + OUTPUT_PATH)
    print("Total slides: " + str(len(prs.slides)))


if __name__ == "__main__":
    main()
