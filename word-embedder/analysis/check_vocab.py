import glob

import pandas as pd

from utils import is_hangul_string

pd.set_option("display.unicode.east_asian_width", True)
pd.set_option("display.max_rows", None)
pd.set_option("display.max_colwidth", 40)

def _iter_dfs(
    xls_files: list[str],
    columns: list[str] | None = None,
    filters: list[callable] | None = None,
):
    for path in xls_files:
        df = pd.read_excel(path)
        if columns:
            missing = [col for col in columns if col not in df.columns]
            if missing:
                raise KeyError(f"컬럼이 존재하지 않습니다: {missing}")
            df = df[columns]
        if filters:
            for f in filters:
                df = df[f(df)]
        yield df


def print_unique_values_by_column(
    xls_files: list[str],
    columns: str | list[str],
    filters: list[callable] | None = None,
):
    if isinstance(columns, str):
        columns = [columns]

    result = {col: set() for col in columns}
    for df in _iter_dfs(xls_files, columns, filters):
        for col in columns:
            result[col].update(df[col].unique())

    for col, values in result.items():
        print(f"{col} : {values}")


def print_samples(
    xls_files: list[str],
    n: int,
    display_columns: list[str] | None = None,
    filters: list[callable] | None = None,
    seed: int = 42,
):
    bucket: pd.DataFrame | None = None
    total = 0

    for df in _iter_dfs(xls_files, display_columns, filters):
        total += len(df)
        bucket = df if bucket is None else pd.concat([bucket, df], ignore_index=True)
        if len(bucket) > n * 3:
            bucket = bucket.sample(n * 3, random_state=seed)

    if bucket is None or bucket.empty:
        print("데이터가 없습니다.")
        return

    print(f"총 {total:,}건")
    print(bucket.sample(min(n, len(bucket)), random_state=seed))


def print_samples_by_unique_value(
    xls_files: list[str],
    column: str,
    n: int,
    display_columns: list[str] | None = None,
    filters: list[callable] | None = None,
    seed: int = 42,
):
    if display_columns is not None and column not in display_columns:
        raise ValueError(f"display_columns에 '{column}'이 포함되어야 합니다.")
    buckets: dict[any, pd.DataFrame] = {}
    counts: dict[any, int] = {}

    for df in _iter_dfs(xls_files, display_columns, filters):
        for value, group in df.groupby(column, dropna=False):
            counts[value] = counts.get(value, 0) + len(group)
            prev = buckets.get(value)
            combined = group if prev is None else pd.concat([prev, group], ignore_index=True)
            # 파일마다 최대 n*3개만 유지해 메모리 제한
            buckets[value] = combined.sample(min(len(combined), n * 3), random_state=seed) if len(combined) > n * 3 else combined

    print(f"\n{'[ 카테고리별 개수 ]'!s:=^40}")
    for value, count in sorted(counts.items(), key=lambda x: -x[1]):
        print(f"  {value!r:15} : {count:,}건")

    for value, rows in buckets.items():
        print(f"\n--- {column} = {value!r} ({counts[value]:,}건) ---")
        print(rows.sample(min(n, len(rows)), random_state=seed))


if __name__ == "__main__":
    XLS_PATH = "data/전체 내려받기_우리말샘_xls_20260402"  # 30개의 xls 파일 존재

    xls_files = sorted(glob.glob(f"{XLS_PATH}/*.xls"))

    # print_unique_values_by_column(xls_files, ["범주"])

    display_columns = ["어휘", "의미 번호", "구성 단위", "품사", "고유어 여부", "범주"]
    filters = [
        lambda df: df["구성 단위"] == "단어",
        lambda df: df["품사"] == "의명·조",
        lambda df: df["범주"].isna(),  # 방언, 북한어, 옛말 제외
        lambda df: df["어휘"].str.replace("-", "", regex=False).apply(is_hangul_string),
    ]

    print_samples(
        xls_files,
        display_columns=display_columns,
        filters=filters,
        n=100,
    )


    # filters = [
    #     lambda df: df["구성 단위"] == "단어",
    #     lambda df: df["범주"].isna(),  # 제외: 방언, 북한어, 옛말
    #     lambda df: df["어휘"].str.replace("-", "", regex=False).apply(is_hangul_string),
    # ]
    # print_samples_by_unique_value(
    #     xls_files,
    #     column="품사",
    #     display_columns=display_columns,
    #     filters=filters,
    #     n=50,
    # )
