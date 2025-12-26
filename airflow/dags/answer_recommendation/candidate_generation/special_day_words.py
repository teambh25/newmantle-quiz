import random
from enum import Enum, auto
from typing import Optional, Tuple


class SpecialDay(Enum):
    신정 = auto()
    정월대보름 = auto()
    설날 = auto()
    삼일절 = auto()
    어린이날 = auto()
    어버이날 = auto()
    부처님오신날 = auto()
    스승의날 = auto()
    대통령선거 = auto()
    현충일 = auto()
    단오 = auto()
    제헌절 = auto()
    광복절 = auto()
    추석 = auto()
    한글날 = auto()
    성탄절 = auto()
    개천절 = auto()


SPECIALDAY_WORDS = {
    SpecialDay.신정: ("새해", "해돋이", "일출", "신년", "첫날", "타종"),
    SpecialDay.정월대보름: (
        "달맞이",
        "부럼",
        "오곡밥",
        "보름달",
        "귀밝이술",
        "쥐불놀이",
    ),
    SpecialDay.설날: ("떡국", "세배", "복주머니", "한복", "차례", "윷놀이"),
    SpecialDay.삼일절: ("태극기", "독립", "만세", "선언", "게양"),
    SpecialDay.어린이날: ("선물", "놀이터", "풍선", "사탕", "놀이공원", "인형"),
    SpecialDay.어버이날: ("카네이션", "감사", "편지", "효도", "선물", "부모님"),
    SpecialDay.부처님오신날: ("연등", "사찰", "법당", "불교", "부처"),
    SpecialDay.스승의날: ("꽃다발", "편지", "선생님", "존경", "감사"),
    SpecialDay.대통령선거: ("투표", "선거", "참정권", "지지율", "국민", "개표"),
    SpecialDay.현충일: ("태극기", "추모", "호국", "선열", "묵념", "헌화", "게양"),
    SpecialDay.단오: ("창포물", "그네", "부채", "한복"),
    SpecialDay.제헌절: ("헌법", "민주주의", "법률", "국가"),
    SpecialDay.광복절: ("자유", "독립", "광복", "해방", "애국심"), 
    SpecialDay.추석: ("송편", "차례", "한가위", "성묘", "보름달", "성묘", "귀성길", "풍요"),
    SpecialDay.한글날: ("한글", "창제", "세종대왕", "언어", "자음", "모음"),
    SpecialDay.성탄절: ("산타", "트리", "선물", "케이크", "루돌프", "예수", "종소리"),
    SpecialDay.개천절: ("단군", "고조선", "홍익", "건국"),
}

SPECIALDAY_BY_DATE = {
    # --- 2025년 ---
    "2025-01-01": SpecialDay.신정,
    "2025-01-13": SpecialDay.정월대보름,
    "2025-01-29": SpecialDay.설날,
    "2025-03-01": SpecialDay.삼일절,
    "2025-05-05": SpecialDay.어린이날,
    "2025-05-08": SpecialDay.어버이날,
    "2025-05-12": SpecialDay.부처님오신날,
    "2025-05-15": SpecialDay.스승의날,
    "2025-06-03": SpecialDay.대통령선거,
    "2025-06-06": SpecialDay.현충일,
    "2025-06-11": SpecialDay.단오,
    "2025-07-17": SpecialDay.제헌절,
    "2025-08-15": SpecialDay.광복절,
    "2025-10-06": SpecialDay.추석,
    "2025-10-09": SpecialDay.한글날,
    "2025-12-25": SpecialDay.성탄절,
    # --- 2026년 ---
    "2026-01-01": SpecialDay.신정,
    "2026-02-01": SpecialDay.정월대보름,
    "2026-02-17": SpecialDay.설날,
    "2026-03-01": SpecialDay.삼일절,
    "2026-05-05": SpecialDay.어린이날,
    "2026-05-08": SpecialDay.어버이날,
    "2026-05-24": SpecialDay.부처님오신날,
    "2026-05-15": SpecialDay.스승의날,
    "2026-06-06": SpecialDay.현충일,
    "2026-06-30": SpecialDay.단오,
    "2026-07-17": SpecialDay.제헌절,
    "2026-08-15": SpecialDay.광복절,
    "2026-09-25": SpecialDay.추석,
    "2026-10-03": SpecialDay.개천절,
    "2026-10-09": SpecialDay.한글날,
    "2026-12-25": SpecialDay.성탄절,
    # --- 2027년 ---
    "2027-01-01": SpecialDay.신정,
    "2027-01-21": SpecialDay.정월대보름,
    "2027-02-07": SpecialDay.설날,
    "2027-03-01": SpecialDay.삼일절,
    "2027-05-05": SpecialDay.어린이날,
    "2027-05-08": SpecialDay.어버이날,
    "2027-05-13": SpecialDay.부처님오신날,
    "2027-05-15": SpecialDay.스승의날,
    "2027-06-06": SpecialDay.현충일,
    "2027-06-19": SpecialDay.단오,
    "2027-07-17": SpecialDay.제헌절,
    "2027-08-15": SpecialDay.광복절,
    "2027-09-15": SpecialDay.추석,
    "2027-10-03": SpecialDay.개천절,
    "2027-10-09": SpecialDay.한글날,
    "2027-12-25": SpecialDay.성탄절,
}


def get_special_day_candidate(date_str: str) -> Optional[Tuple[str]]:
    special_day = SPECIALDAY_BY_DATE.get(date_str)
    if special_day is None:
        return None
    words = SPECIALDAY_WORDS[special_day]
    candidates = [
        {"word": w, "tag": "기념일", "description": f"오늘은 {special_day.name}입니다."}
        for w in words
    ]
    random.shuffle(candidates)
    return candidates
