import argparse

# from dotenv import dotenv_values
from loguru import logger
import requests

from config import configs, Config

logger.remove()  # Remove default console handler
logger.add(
    "./logs/quiz-register.log",
    rotation=None,
    retention=None,
    format="{time:YYYY-MM-DD HH:mm:ss!UTC} | {level} | {message}",
)


def call_upsert_quiz(configs: Config, quiz: dict):
    url = f"{configs.GAME_SERVER_URL}/admin/quizzes"
    try:
        response = requests.put(
            url,
            json=quiz,
            auth=(configs.ADMIN_ID, configs.ADMIN_PW),
            timeout=5
        )
        response.raise_for_status()
        logger.success("Request succeeded!")
        logger.success(f"Server response: {response.json()}")
    except requests.exceptions.HTTPError as err:
        logger.error(f"HTTP error occurred: {err}")
        logger.error(f"Response content: {response.text}")
    except requests.exceptions.ConnectionError as err:
        logger.error(f"Connection error occurred: {err}")
    except requests.exceptions.Timeout as err:
        logger.error(f"Request timed out: {err}")
    except requests.exceptions.RequestException as err:
        logger.error(f"An unknown error occurred: {err}")
    

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", type=str, required=True, help="Date in YYYY-MM-DD format")
    args = parser.parse_args()
    quiz = {
        "date": args.date,
        "answer": "정답",
        "scores": {
            "사과": 0.98,
            "바나나": 0.89,
            "딸기": 0.77
        }
    }
    call_upsert_quiz(configs, quiz)