import os
import argparse

import torch
from loguru import logger

from utils import load_init_words
from models import load_model_and_tokenizer, inference
from dataset import preprocessing

logger.remove()  # Remove default console handler
logger.add(
    "./logs/word-embedder.log",
    rotation=None,
    retention=None,
    format="{time:YYYY-MM-DD HH:mm:ss!UTC} | {level} | {message}",
)

MODEL_NAME = "kakaobank/kf-deberta-base"
INIT_DATA_PATH = "data/ko-aff-dic-0.7.92/ko.dic"
SAVE_EMBEDDING_PATH = "data/embedding/init-data"
SAVE_ITER = 10000
BATCH_SIZE = 128

if __name__ == "__main__":
    print(f"Using device: {'cuda' if torch.cuda.is_available() else 'cpu'}")

    parser = argparse.ArgumentParser()
    parser.add_argument("--init", action="store_true")
    args = parser.parse_args()

    if args.init:
        words = load_init_words(INIT_DATA_PATH)
        save_path = SAVE_EMBEDDING_PATH
    else:
        pass

    os.makedirs(save_path, exist_ok=True)
    
    model, tokenizer = load_model_and_tokenizer(MODEL_NAME)
    dataset = preprocessing(words, tokenizer)
    inference(
        dataset=dataset,
        model=model,
        tokenizer=tokenizer,
        batch_size=BATCH_SIZE,
        save_path=save_path,
        save_iter=SAVE_ITER,
    )