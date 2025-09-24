from datetime import datetime


def get_korean_season(date_str: str) -> str:
    date = datetime.strptime(date_str, "%Y-%m-%d")
    month = date.month
    day = date.day

    if month == 12:
        return "초겨울" if day < 16 else "한겨울"
    elif month == 1:
        return "한겨울" if day < 16 else "늦겨울"
    elif month == 2:
        return "늦겨울" if day < 16 else "초봄"
    elif month == 3:
        return "초봄" if day < 16 else "봄"
    elif month == 4:
        return "봄" if day < 16 else "늦봄"
    elif month == 5:
        return "늦봄" if day < 16 else "초여름"
    elif month == 6:
        return "초여름" if day < 16 else "한여름"
    elif month == 7:
        return "한여름" if day < 16 else "늦여름"
    elif month == 8:
        return "늦여름" if day < 16 else "초가을"
    elif month == 9:
        return "초가을" if day < 16 else "가을"
    elif month == 10:
        return "가을" if day < 16 else "늦가을"
    elif month == 11:
        return "늦가을" if day < 16 else "초겨울"
    else:
        raise ValueError("올바른 날짜를 입력해주세요.")
