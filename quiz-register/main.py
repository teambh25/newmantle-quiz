import datetime

import argparse
from loguru import logger

from config import configs
from register_quiz import register_quiz
from quiz import Quiz

logger.remove()  # Remove default console handler
logger.add(
    "./logs/quiz-register.log",
    rotation=None,
    retention=None,
    format="{time:YYYY-MM-DD HH:mm:ss!UTC} | {level} | {message}",
)

def valid_date(s: str) -> datetime.date:
    try:
        return datetime.datetime.strptime(s, "%Y-%m-%d").date()
    except ValueError:
        raise argparse.ArgumentTypeError(f"Not a valid date: '{s}'. Expected format: YYYY-MM-DD")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", type=str, required=valid_date, help="Date in YYYY-MM-DD format")
    parser.add_argument("--answer", type=str, required=True, help="Answer Word")
    args = parser.parse_args()
    
    quiz = Quiz(configs, args.date, args.answer)
    register_quiz(configs, quiz)