import argparse
import os

import torch
from dotenv import load_dotenv
from dataset import preprocessing
from loguru import logger
from models import inference, load_model_and_tokenizer
from utils import load_words, save_embedding, save_to_db

load_dotenv()

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
    parser.add_argument(
        "--input_words",
        type=str,
        required=True,
        help="Path to a file containing words to generate embeddings (one word per line)",
    )
    parser.add_argument(
        "--batch_size", type=int, default=128, help="Number of samples per batch"
    )
    parser.add_argument(
        "--save_path",
        type=str,
        default="data/embedding",
        help="Directory path where the embedding CSV will be saved",
    )
    parser.add_argument(
        "--output_npz", type=str, required=True, help="npz filename for saving the embedding"
    )
    parser.add_argument("--save_db", action="store_true", help="Save embeddings to PostgreSQL")
    args = parser.parse_args()

    os.makedirs(args.save_path, exist_ok=True)
    npz_path = os.path.join(args.save_path, args.output_npz)

    hf_home = os.environ["HF_HOME"]

    words = load_words(args.input_words)
    model, tokenizer = load_model_and_tokenizer(MODEL_NAME, cache_dir=hf_home)
    dataset = preprocessing(words, tokenizer)
    embeddings = inference(
        dataset=dataset,
        model=model,
        tokenizer=tokenizer,
        batch_size=args.batch_size,
    )
    save_embedding(npz_path, embeddings)

    if args.save_db:
        save_to_db(
            embedding=embeddings,
            host=os.environ["DB_HOST"],
            port=int(os.environ.get("DB_PORT", 5432)),
            dbname=os.environ["DB_NAME"],
            user=os.environ["DB_USER"],
            password=os.environ["DB_PASSWORD"],
        )
