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

if __name__ == "__main__":
    print(f"Using device: {'cuda' if torch.cuda.is_available() else 'cpu'}")

    parser = argparse.ArgumentParser()
    parser.add_argument("--init", action="store_true")
    parser.add_argument("--save_path", type=str, required=True, help="path to save embedding")
    parser.add_argument("--save_iter", type=int, default=10000, help="step to save embedding")
    parser.add_argument("--batch_size", type=int, default=128, help="number of samples per batch")
    args = parser.parse_args()

    if args.init:
        INIT_DATA_PATH = "data/ko-aff-dic-0.7.92/ko.dic"
        words = load_init_words(INIT_DATA_PATH)
    else:
        pass

    os.makedirs(args.save_path, exist_ok=True)
    
    model, tokenizer = load_model_and_tokenizer(MODEL_NAME)
    dataset = preprocessing(words, tokenizer)
    inference(
        dataset=dataset,
        model=model,
        tokenizer=tokenizer,
        batch_size=args.batch_size,
        save_path=args.save_path,
        save_iter=args.save_iter,
    )