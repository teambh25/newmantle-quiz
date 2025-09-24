import json
import random
import re
from datetime import datetime, timedelta
from pathlib import Path


def add_days(date_str: str, days: int) -> str:
    date_obj = datetime.strptime(date_str, "%Y-%m-%d")
    next_day = date_obj + timedelta(days=days)
    return next_day.strftime("%Y-%m-%d")


def gemini_resp_to_dict(resp: str):
    match = re.search(r"```json\s*(.*?)\s*```", resp, re.DOTALL)
    if not match:
        raise ValueError("Can't find Json", resp)
    json_str = match.group(1).strip()

    try:
        data = json.loads(json_str)
    except json.JSONDecodeError:
        raise ValueError("Fail to parsing json", resp)
    return data


def is_hangul_char(ch: str) -> bool:
    """function currently returns True only for 가~힣"""
    code = ord(ch)
    return 0xAC00 <= code <= 0xD7A3  # 가 ~ 힣


def is_hangul_string(s: str) -> bool:
    return s != "" and all(is_hangul_char(ch) for ch in s)


def json_to_str(items: list) -> str:
    return json.dumps(items, ensure_ascii=False, indent=2)


def load_and_fill_prompt(path: Path, fill_data: str = None) -> str:
    """
    load prompt and fill {{ data }} in prompt
    """
    with open(path, "r", encoding="utf-8") as f:
        prompt = f.read()
    if fill_data is not None:
        prompt = prompt.replace("{{ data }}", fill_data)
    return prompt


def scaler_factory(min_dist: float):
    def scaler(x: float) -> float:
        """
        1. Min-Max Scaling: scale x from range [min_dist, max_dist] to [0, 1]
        2. Convert the [0, 1] range to [0, 100]
        """
        x = (x - min_dist) / (1 - min_dist)  # max_dist = 1 (answer)
        return round(x * 100, 2)

    return scaler


def with_prob(prob: float):
    return random.random() < prob
