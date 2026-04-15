import glob

import pandas as pd
from utils import is_hangul_string

XLS_PATH = "data/전체 내려받기_우리말샘_xls_20260402"
INIT_WORDS_PATH = "data/embedding/init_words_v1.txt"


def process(df: pd.DataFrame) -> pd.Series:
    df = df[df["구성 단위"] == "단어"]
    df = df[df["품사"].isin(["명사", "동사", "형용사"])]
    df = df[df["범주"].isna()] # 방언, 북한어, 옛말 제외
    words = df["어휘"].str.replace("-", "", regex=False)
    return words[words.apply(is_hangul_string)]


if __name__ == "__main__":
    xls_files = sorted(glob.glob(f"{XLS_PATH}/*.xls"))
    results = []

    for i, path in enumerate(xls_files):
        print(f"[{i + 1}/{len(xls_files)}] {path}")
        df = pd.read_excel(path)
        words = process(df)
        print(f"{len(words)} words")
        results.append(words)

    all_words = pd.concat(results, ignore_index=True).drop_duplicates()
    print(f"### {len(all_words)} words ###")

    with open(INIT_WORDS_PATH, "w", encoding="utf-8") as f:
        for word in all_words:
            f.write(word + "\n")

    print(f"Saved to {INIT_WORDS_PATH}")
