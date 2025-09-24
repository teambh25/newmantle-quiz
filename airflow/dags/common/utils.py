from datetime import datetime, timedelta
import json
from pathlib import Path
import re
import random


def add_days(date_str: str, days: int) -> str:
    date_obj = datetime.strptime(date_str, "%Y-%m-%d")
    next_day = date_obj + timedelta(days=days)
    return next_day.strftime("%Y-%m-%d")


def fill_prompt(template: str, data: str) -> str:
    return template.replace("{{ data }}", data)


def gemini_resp_to_dict(resp: str):
    match = re.search(r"```json\s*(.*?)\s*```", resp, re.DOTALL)
    if not match:
        raise ValueError("Can't find Json", resp)
    json_str = match.group(1).strip()
    
    try:    
        data = json.loads(json_str)
    except json.JSONDecodeError as e:
        raise ValueError(f"Fail to parsing json", resp)
    return data


def is_hangul_char(ch: str) -> bool:
    """ function currently returns True only for 가~힣 """
    code = ord(ch)
    return 0xAC00 <= code <= 0xD7A3  # 가 ~ 힣


def is_hangul_string(s: str) -> bool:
    return s != "" and all(is_hangul_char(ch) for ch in s)


def json_to_str(items: list) -> str:
    return json.dumps(items, ensure_ascii=False, indent=2)


def load_prompt(path: Path) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def with_prob(prob: float):
    return random.random() < prob