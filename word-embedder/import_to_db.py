"""Load existing npz embeddings into PostgreSQL.

Usage:
    python import_to_db.py --npz_path data/embedding/init.npz
"""

import argparse
import os

from dotenv import load_dotenv
from utils import load_embedding, save_to_db

load_dotenv()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--npz_path", type=str, required=True, help="Path to npz file")
    args = parser.parse_args()

    embedding = load_embedding(args.npz_path)
    print("load embedding success !!")
    save_to_db(
        embedding=embedding,
        host=os.environ["DB_HOST"],
        port=int(os.environ.get("DB_PORT", 5432)),
        dbname=os.environ["DB_NAME"],
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
    )
