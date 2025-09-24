import os
from dataclasses import dataclass
from pathlib import Path

INTERVAL_DAYS = 90

# LLM config
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
GEMINI_MODEL = "gemini-2.5-flash"


# Prompts
@dataclass(frozen=True)
class PromptPaths:
    BASE_DIR = Path("dags/common/llm/prompts")
    COMMON_SENSE = BASE_DIR / "news_common_sense_words.md"
    TREND = BASE_DIR / "search_trend_words.md"
    DAILY = BASE_DIR / "daily_words.md"


PROMPTS = PromptPaths()

# Use Special day
SPECIAL_DAY_PROB = 0.5
