import glob
import zipfile
from io import BytesIO

import pandas as pd


def load_logs(zip_paths: list[str]) -> pd.DataFrame:
    frames = []
    for zip_path in sorted(zip_paths):
        with zipfile.ZipFile(zip_path, "r") as zf:
            for name in zf.namelist():
                with zf.open(name) as f:
                    df = pd.read_json(BytesIO(f.read()), lines=True)
                    print(f"{zip_path} / {name}: {len(df):,} rows")
                    frames.append(df)

    result = pd.concat(frames, ignore_index=True)
    result["correct"] = result["correct"].astype("boolean")
    print(f"\nTotal: {len(result):,} log entries from {len(zip_paths)} files")
    return result


def print_action_counts(df: pd.DataFrame) -> None:
    action_counts = df.groupby(["date", "action"]).size().unstack(fill_value=0)
    print("[ action counts ]")
    print(action_counts)


def print_user_summary(df: pd.DataFrame) -> None:
    unique_users = df.groupby("date")["user_id"].nunique().rename("unique_users")

    correct_users = (
        df[df["action"] == "guess"]
        .groupby("date")
        .apply(lambda g: g.loc[g["correct"] == True, "user_id"].nunique())
        .rename("correct_users")
    )

    give_up_users = (
        df[df["action"] == "give_up"]
        .groupby("date")["user_id"]
        .nunique()
        .rename("give_up_users")
    )

    user_summary = pd.concat([unique_users, correct_users, give_up_users], axis=1).fillna(0)
    user_summary[["correct_users", "give_up_users"]] = user_summary[
        ["correct_users", "give_up_users"]
    ].astype(int)
    print("\n[ user summary ]")
    print(user_summary)


def print_duplicate_guess(df: pd.DataFrame) -> None:
    guess_df = df[df["action"] == "guess"]
    total_guess = guess_df.groupby("date").size().rename("total_guess")
    unique_user_word_guess = (
        guess_df.drop_duplicates(subset=["date", "user_id", "word"])
        .groupby("date")
        .size()
        .rename("unique_user_word_guess")
    )
    dup_summary = pd.concat([total_guess, unique_user_word_guess], axis=1).fillna(0).astype(int)
    dup_summary["duplicate"] = dup_summary["total_guess"] - dup_summary["unique_user_word_guess"]
    dup_summary["dup_%"] = (
        dup_summary["duplicate"] / dup_summary["total_guess"].replace(0, pd.NA) * 100
    ).round(2)
    print("\n[ duplicate guess by same user on same word ]")
    print(dup_summary)


def print_user_type_ratio(df: pd.DataFrame) -> None:
    user_type_by_date = (
        df.drop_duplicates(subset=["date", "user_id"])
        .groupby(["date", "user_type"])
        .size()
        .unstack(fill_value=0)
    )
    user_type_by_date["total"] = user_type_by_date.sum(axis=1)
    for col in [c for c in user_type_by_date.columns if c != "total"]:
        user_type_by_date[f"{col}%"] = (
            user_type_by_date[col] / user_type_by_date["total"] * 100
        ).round(1)
    print("\n[ user_type per date (unique users) ]")
    print(user_type_by_date)


if __name__ == "__main__":
    zip_paths = glob.glob("data/game-event-logs/*.jsonl.zip")
    df = load_logs(zip_paths)

    print_action_counts(df)
    print_user_summary(df)
    print_user_type_ratio(df)
    print_duplicate_guess(df)

    print("\n[ samples ]")
    print(df.head())
