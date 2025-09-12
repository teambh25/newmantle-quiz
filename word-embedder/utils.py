import os
import csv

import unicodedata
from typing import List, Dict

import numpy as np
from loguru import logger


def load_init_words(path: str) -> List[str]:
    words = set()
    with open(path, 'r', encoding='utf-8') as f:
        for line in f.readlines():
            word = line.split('/')[0]
            word = unicodedata.normalize('NFC', word)
            word = word.rstrip("\n")
            if is_hangul_string(word):
               words.add(word)
    return list(words)


def is_hangul_char(ch: str) -> bool:
        """ function currently returns True only for 가~힣 """
        code = ord(ch)
        return 0xAC00 <= code <= 0xD7A3  # 가 ~ 힣

def is_hangul_string(s: str) -> bool:
    return s != "" and all(is_hangul_char(ch) for ch in s)


def has_hangul_string(s: str) -> bool:
    return s != "" and any(is_hangul_char(ch) for ch in s)


def filter_special_token_word(tokenizer, data: List):
    return [word for word in data if not has_speical_token(tokenizer.tokenize(word))]


def has_speical_token(tokens: List[str]) -> bool:
    for t in tokens:
        if t[0] == "[" and t[-1] == "]":
            return True
    return False


def save_embedding(csv_path:str, embedding:Dict[str, np.ndarray]):
    try:
        if os.path.exists(csv_path):
            raise FileExistsError(f"The file '{csv_path}' already exists.")
        with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['word', 'emb'])  # write header
            for word, vector in embedding.items():
                vector_string = str(vector.tolist())  # pgvector readable format : "[v1,v2,v3,...]"
                writer.writerow([word, vector_string])
        msg = f"Successfully saved {len(embedding)} embeddings to {csv_path}"
        print(msg)
        logger.info(msg)
    except Exception as e:
        msg =f"Error saving CSV file: {e}"
        print(msg)
        logger.error(msg)