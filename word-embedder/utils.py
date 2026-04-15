import os
from typing import Dict, List

import numpy as np
import psycopg
from pgvector.psycopg import register_vector
from loguru import logger


def load_words(path: str) -> List[str]:
    with open(path, "r", encoding="utf-8") as f:
        return [line.rstrip("\n") for line in f if line.strip()]


def _is_hangul_char(ch: str) -> bool:
    """function currently returns True only for 가~힣"""
    code = ord(ch)
    return 0xAC00 <= code <= 0xD7A3  # 가 ~ 힣


def is_hangul_string(s: str) -> bool:
    return s != "" and all(_is_hangul_char(ch) for ch in s)


def filter_special_token_word(tokenizer, data: List):
    return [word for word in data if not has_speical_token(tokenizer.tokenize(word))]


def has_speical_token(tokens: List[str]) -> bool:
    for t in tokens:
        if t[0] == "[" and t[-1] == "]":
            return True
    return False


def load_embedding_words(npz_path: str) -> List[str]:
    return np.load(npz_path)["words"].tolist()


def load_embedding(npz_path: str) -> Dict[str, np.ndarray]:
    data = np.load(npz_path)
    return dict(zip(data["words"].tolist(), data["embeddings"]))


def save_to_db(embedding: Dict[str, np.ndarray], host: str, port: int, dbname: str, user: str, password: str):
    with psycopg.connect(host=host, port=port, dbname=dbname, user=user, password=password) as conn:
        register_vector(conn)
        with conn.cursor() as cur:
            with cur.copy("COPY vocabulary (word, emb) FROM STDIN WITH (FORMAT BINARY)") as copy:
                copy.set_types(["text", "vector"])

                count = 0
                for word, emb in embedding.items():
                    copy.write_row((word, emb))
                    count += 1
                    while conn.pgconn.flush() == 1:
                        pass
                    if count % 10000 == 0:
                        print(f"[{count}] rows copied...")
        conn.commit()
        msg = f"Saved {len(embedding)} embeddings to DB"
        print(msg)
        logger.info(msg)

def save_embedding(npz_path: str, embedding: Dict[str, np.ndarray]):
    try:
        if os.path.exists(npz_path):
            raise FileExistsError(f"The file '{npz_path}' already exists.")
        words = list(embedding.keys())
        embeddings = np.array(list(embedding.values()), dtype=np.float32)
        np.savez_compressed(npz_path, words=np.array(words), embeddings=embeddings)
        msg = f"Successfully saved {len(embedding)} embeddings to {npz_path}"
        print(msg)
        logger.info(msg)
    except Exception as e:
        msg = f"Error saving npz file: {e}"
        print(msg)
        logger.error(msg)
