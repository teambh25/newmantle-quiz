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
            if is_hangul(word):
               words.add(word)
    return list(words)


def filter_special_token_word(tokenizer, data: List):
    return [word for word in data if not has_speical_token(tokenizer.tokenize(word))]


def is_hangul(text: str) -> bool:
    return bool(re.match(r'^[\uAC00-\uD7A3]+$', text)) # check text are entirely korean (w/o jamo)


def has_speical_token(tokens: List[str]) -> bool:
    for t in tokens:
        if t[0] == "[" and t[-1] == "]":
            return True
    return False


def save_embedding(file_name:str, embedding:Dict[str, np.ndarray]):
    with open(file_name, 'wb') as pickle_file:
        pickle.dump(embedding, pickle_file)
        logger.info(f"{file_name} is saved!!")
