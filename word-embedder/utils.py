import re
import pickle
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


def save_embedding(file_name:str, embedding:Dict[str, np.ndarray]):
    with open(file_name, 'wb') as pickle_file:
        pickle.dump(embedding, pickle_file)
        logger.info(f"{file_name} is saved!!")
