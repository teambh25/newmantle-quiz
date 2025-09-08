import requests
from loguru import logger

from config import Configs
from quiz import Quiz

def register_quiz(configs: Configs, quiz: Quiz):
    url = f"{configs.server_url}/admin/quizzes"
    try:
        response = requests.put(
            url,
            json=quiz.to_dict(),
            auth=(configs.server_id, configs.server_pw),
            timeout=5
        )
        response.raise_for_status()
        logger.success(f"Request to {configs.server_url} succeeded!")
        logger.success(f"Server response: {response.json()}")
        print(f"register quiz success in {configs.server_url} : {response.json()}")
    except requests.exceptions.HTTPError as err:
        logger.error(f"HTTP error occurred: {err}")
        logger.error(f"Response content: {response.text}")
    except requests.exceptions.ConnectionError as err:
        logger.error(f"Connection error occurred: {err}")
    except requests.exceptions.Timeout as err:
        logger.error(f"Request timed out: {err}")
    except requests.exceptions.RequestException as err:
        logger.error(f"An unknown error occurred: {err}")