import json
import random
import re
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

def add_days(date_str: str, days: int) -> str:
    date_obj = datetime.strptime(date_str, "%Y-%m-%d")
    next_day = date_obj + timedelta(days=days)
    return next_day.strftime("%Y-%m-%d")

def subtract_days(date_str: str, days: int) -> str:
    date_obj = datetime.strptime(date_str, "%Y-%m-%d")
    new_date = date_obj - timedelta(days=days)
    return new_date.strftime("%Y-%m-%d")

def is_future(date_str: str) -> bool:
    today_str = datetime.now(ZoneInfo('Asia/Seoul')).strftime("%Y-%m-%d")
    return date_str > today_str

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

def load_and_fill_prompt(path: Path, fill_data: str = None) -> str:
    """
    load prompt and fill {{ data }} in prompt
    """
    with open(path, "r", encoding="utf-8") as f:
        prompt = f.read()
    if fill_data is not None:
        prompt = prompt.replace("{{ data }}", fill_data)
    return prompt

def is_hangul_char(ch: str) -> bool:
    """function currently returns True only for 가~힣"""
    code = ord(ch)
    return 0xAC00 <= code <= 0xD7A3  # 가 ~ 힣


def is_hangul_string(s: str) -> bool:
    return s != "" and all(is_hangul_char(ch) for ch in s)


def json_to_str(items: list) -> str:
    return json.dumps(items, ensure_ascii=False, indent=2)


def with_prob(prob: float):
    return random.random() < prob


def save_temp_json(data: dict, prefix: str) -> str:
    """Save JSON to a temporary file. Returns file path."""
    with tempfile.NamedTemporaryFile(
        mode="w", delete=False, prefix=prefix, suffix=".json"
    ) as f:
        json.dump(data, f)
        print(f"Saved file : {f.name}")
        return f.name

def load_json(path: str):
    with open(path, "r") as f:
        return json.load(f)