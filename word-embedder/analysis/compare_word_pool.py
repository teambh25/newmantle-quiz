import sys

sys.path.append(".")

from utils import load_embedding_words

EMBEDDING_CSV_PATH = "data/embedding/ko-aff-dict.csv"
NEW_WORDS_TXT_PATH = "data/embedding/init_words_v1.txt"


def load_txt_words(path: str) -> set[str]:
    with open(path, "r", encoding="utf-8") as f:
        return {line.rstrip("\n") for line in f if line.strip()}


if __name__ == "__main__":
    # ko-aff-dict.csv vs init_words_v1.txt
    words = load_embedding_words(EMBEDDING_CSV_PATH)

    print(f"[ko-aff-dict.csv vs init_words_v1.txt]")

    csv_words = set(words)
    txt_words = load_txt_words(NEW_WORDS_TXT_PATH)

    only_in_csv = csv_words - txt_words
    only_in_txt = txt_words - csv_words
    in_both = csv_words & txt_words

    print(f"  ko-aff-dict.csv 단어 수       : {len(csv_words)}")
    print(f"  init_words_v1.txt 단어 수: {len(txt_words)}")
    print(f"  공통 단어 수           : {len(in_both)}")
    print(f"  csv에만 있는 단어 수   : {len(only_in_csv)}")
    print(f"  txt에만 있는 단어 수   : {len(only_in_txt)}")

    with open("data/analysis/only_in_csv.txt", "w", encoding="utf-8") as f:
        for word in sorted(only_in_csv):
            f.write(word + "\n")
    print(f"  -> csv에만 있는 단어 저장: data/analysis/only_in_csv.txt")

    with open("data/analysis/only_in_txt.txt", "w", encoding="utf-8") as f:
        for word in sorted(only_in_txt):
            f.write(word + "\n")
    print(f"  -> txt에만 있는 단어 저장: data/analysis/only_in_txt.txt")
