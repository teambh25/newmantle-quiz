import argparse

from loguru import logger
import psycopg
from pgvector.psycopg import register_vector

from config import configs
from utils import load_embedding
from setup import create_answer_table, create_vocaburary_table, insert_embedding

logger.remove()  # Remove default console handler
logger.add(
    "./logs/data-loader.log",
    rotation=None,
    retention=None,
    format="{time:YYYY-MM-DD HH:mm:ss!UTC} | {level} | {message}",
)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--setup", action="store_true")
    parser.add_argument("--emb_path", type=str, required=True, help="embedding path")
    args = parser.parse_args()
    
    url = f"postgresql://{configs.DB_USER}:{configs.DB_PW}@postgres:5432/{configs.DB_NAME}"
    conn = psycopg.connect(url, autocommit=True)
    register_vector(conn)
    embeddings = load_embedding(args.emb_path)
    logger.info(f"# embeddings : {len(embeddings)}")
    print(f"# embeddings : {len(embeddings)}")

    if args.setup:
        conn.execute('CREATE EXTENSION IF NOT EXISTS vector')
        create_vocaburary_table(conn, configs.EMB_DIM)
        create_answer_table(conn)
        
    insert_embedding(conn, embeddings)