import os
import argparse

import torch
from loguru import logger

from utils import load_init_words, save_embedding
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
INIT_WORDS_PATH = "data/ko-aff-dic-0.7.92/ko.dic"

if __name__ == "__main__":
    print(f"Using device: {'cuda' if torch.cuda.is_available() else 'cpu'}")

    parser = argparse.ArgumentParser()
    parser.add_argument("--init", action="store_true", help="Initialize embeddings with default words")
    parser.add_argument("--batch_size", type=int, default=128, help="Number of samples per batch")
    parser.add_argument("--input_words", type=str, help="Path to a file containing words to generate embeddings")
    parser.add_argument("--save_path", type=str, default="data/embedding", help="Directory path where the embedding CSV will be saved")
    parser.add_argument("--csv_name", type=str, help="CSV name for saving the embedding")
    args = parser.parse_args()

    os.makedirs(args.save_path, exist_ok=True)
    if args.init:
        words = load_init_words(INIT_WORDS_PATH)
        csv_path = os.path.join(args.save_path, "init.csv") 
    else:
        if args.input_words is None:
            parser.error("--input_words is required if --init is not set")
        # words = load_words(input_words)
        if args.csv_name is None:
            parser.error("--csv_name is required if --init is not set")
        csv_path = os.path.join(args.save_path, args.csv_name) 
    
    model, tokenizer = load_model_and_tokenizer(MODEL_NAME)
    dataset = preprocessing(words, tokenizer)
    embeddings = inference(
        dataset=dataset,
        model=model,
        tokenizer=tokenizer,
        batch_size=args.batch_size,
    )
    save_embedding(csv_path, embeddings)