from enum import Enum, auto
from typing import Tuple


class Season(Enum):
    spring = auto()
    summer = auto()
    fall = auto()
    winter = auto()

_SEASON_WORDS = {
    Season.spring: (
        "벚꽃", "나들이", "딸기", "봄나물", "꽃샘추위",
        "개나리", "진달래", "씨앗", "봄비", "새싹",
        "봄꽃축제", "나비", "봄바람", "꽃구경", "새싹채소",
        "봄향기", "꽃다발", "산책", "화분", "유채꽃"
    ),
    Season.summer: (
        "수박", "아이스크림", "해수욕", "삼계탕", "선풍기",
        "바닷가", "모기", "캠핑", "바캉스", "에어컨",
        "빙수", "자외선", "수영", "소나기", "햇볕",
        "토마토", "여름휴가", "밤바다", "선글라스", "냉면", 
        '장마', '피서', '계곡', '물놀이'
    ),
    Season.fall: (
        "사과", "단풍", "호박", "밤", "송편",
        "독서", "추수", "코스모스", "낙엽", "감",
        "버섯", "가을비", "천고마비", "은행", "오곡밥",
        "가을바람", "밤하늘", "포도", "곶감"
    ),
    Season.winter: (
        "어묵", "김장", "눈사람", "군고구마", "붕어빵",
        "크리스마스", "겨울왕국", "코트", "목도리", "장갑",
        "눈송이", "온돌", "스키", "겨울바다", "눈싸움",
        "보일러", "핫초코", "겨울축제", "성탄절", "연말",
        "귤"
    )
}


def get_season_words(date_str: str) -> Season:
    month = int(date_str[5:7])
    if 3 <= month <= 5:
        return _SEASON_WORDS[Season.spring]
    elif 6 <= month <= 8:
        return _SEASON_WORDS[Season.summer]
    elif 9 <= month <= 11:
        return _SEASON_WORDS[Season.fall]
    else:  # 12, 1, 2
        return _SEASON_WORDS[Season.winter]