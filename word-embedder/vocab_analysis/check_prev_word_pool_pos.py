import pickle
import sys

sys.path.append(".")

from utils import load_embedding_words

EMBEDDING_CSV_PATH = "data/embedding/init.csv"
WORD_POS_DICT_PATH = "data/analysis/word_pos_dict.pkl"


if __name__ == "__main__":
    words = load_embedding_words(EMBEDDING_CSV_PATH)

    with open(WORD_POS_DICT_PATH, "rb") as f:
        word_pos_dict: dict[str, set] = pickle.load(f)

    in_dict = [w for w in words if w in word_pos_dict]
    not_in_dict = [w for w in words if w not in word_pos_dict]

    print(f"pos_dict에 있는 단어 수: {len(in_dict)}")
    print(f"pos_dict에 없는 단어 수: {len(not_in_dict)}")

    with open("data/analysis/tmp.txt", "w", encoding="utf-8") as f:
        for word in not_in_dict:
            f.write(word + "\n")