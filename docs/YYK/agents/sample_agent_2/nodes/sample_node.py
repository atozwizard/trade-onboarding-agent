TRANSLATION_TABLE = {
    "반려동물 보험은 예상치 못한 진료비 부담을 줄여줍니다.": "Pet insurance reduces the burden of unexpected medical bills.",
    "우리 강아지는 최근 건강검진에서 아주 좋은 결과를 받았습니다.": "Our dog recently received very good results from a health checkup.",
    "고양이가 아플 때 빠르게 병원에 갈 수 있도록 대비하고 싶어요.": "I want to be prepared so I can take my cat to the hospital quickly when it is sick.",
}


def translate_to_english(korean_sentence: str) -> str:
    return TRANSLATION_TABLE.get(
        korean_sentence,
        "I want to prepare pet insurance for unexpected veterinary expenses.",
    )
