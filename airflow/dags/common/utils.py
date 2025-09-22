def is_hangul_char(ch: str) -> bool:
    """ function currently returns True only for 가~힣 """
    code = ord(ch)
    return 0xAC00 <= code <= 0xD7A3  # 가 ~ 힣


def is_hangul_string(s: str) -> bool:
    return s != "" and all(is_hangul_char(ch) for ch in s)


def load_prompt(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()
    

