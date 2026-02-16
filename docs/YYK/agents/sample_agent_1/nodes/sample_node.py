import random


KOREAN_SENTENCES = [
    "반려동물 보험은 예상치 못한 진료비 부담을 줄여줍니다.",
    "우리 강아지는 최근 건강검진에서 아주 좋은 결과를 받았습니다.",
    "고양이가 아플 때 빠르게 병원에 갈 수 있도록 대비하고 싶어요.",
]


def generate_korean_sentence() -> str:
    return random.choice(KOREAN_SENTENCES)
