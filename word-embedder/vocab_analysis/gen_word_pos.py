import glob
import pickle

import pandas as pd
from utils import is_hangul_string

XLS_PATH = "data/전체 내려받기_우리말샘_xls_20260402"  # 30개의 xls 파일 존재
WORD_POS_DICT_PATH = "data/analysis/word_pos_dict.pkl"

def process(df: pd.DataFrame) -> pd.DataFrame:
    df = df[["어휘", "품사"]]
    df = df[df["구성 단위"] == "단어"]
    df["어휘"] = df["어휘"].str.replace("-", "", regex=False)
    df = df[df["어휘"].apply(lambda x: is_hangul_string(x))]
    return df


if __name__ == "__main__":
    xls_files = sorted(glob.glob(f"{XLS_PATH}/*.xls"))
    results = []

    for i, path in enumerate(xls_files):
        print(f"[{i + 1}/{len(xls_files)}] {path}")
        df = pd.read_excel(path)
        df = process(df)
        print(f"{len(df)} words")
        results.append(df)

    final = pd.concat(results, ignore_index=True)
    print(f"### {len(final)} rows ###")

    word_pos_dict = final.groupby("어휘")["품사"].apply(set).to_dict()
    print(f"### {len(word_pos_dict)} words ###")

    with open(WORD_POS_DICT_PATH, "wb") as f:
        pickle.dump(word_pos_dict, f)
