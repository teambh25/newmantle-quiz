import glob

import pandas as pd

from log_analysis.overview import load_logs
from utils import is_hangul_string


def prepare_invalid_df(df: pd.DataFrame) -> pd.DataFrame:
    invalid_df = df[df["action"] == "guess_invalid_word"].copy()
    invalid_df["is_hangul"] = invalid_df["word"].map(
        lambda w: isinstance(w, str) and is_hangul_string(w)
    )
    return invalid_df


def drop_non_hangul_invalid(df: pd.DataFrame) -> pd.DataFrame:
    non_hangul_mask = (df["action"] == "guess_invalid_word") & df["word"].map(
        lambda w: not (isinstance(w, str) and is_hangul_string(w))
    )
    return df[~non_hangul_mask].reset_index(drop=True)


def print_date_summary(df: pd.DataFrame, invalid_df: pd.DataFrame):
    total_guess = (
        df[df["action"].isin(["guess", "guess_invalid_word"])]
        .groupby("date")
        .size()
        .rename("total_guess")
    )
    hangul_counts = (
        invalid_df.groupby("date")["is_hangul"]
        .value_counts()
        .unstack(fill_value=0)
        .rename(columns={True: "hangul_true", False: "hangul_false"})
    )

    counts = pd.concat([total_guess, hangul_counts], axis=1).fillna(0).astype(int)
    summary = pd.DataFrame(index=counts.index)
    summary["total_guess"] = counts["total_guess"]
    summary["total_invalid"] = counts["hangul_true"] + counts["hangul_false"]
    summary["inv/guess_%"] = (summary["total_invalid"] / counts["total_guess"] * 100).round(2)
    summary["hangul/guess_%"] = (counts["hangul_true"] / counts["total_guess"] * 100).round(2)
    summary["non-hangul/inv_%"] = (counts["hangul_false"] / summary["total_invalid"] * 100).round(2)

    print("[ invalid word counts per date ]")
    print(summary)


def print_word_stats(df: pd.DataFrame, top_n: int = 100):
    invalid_df = df[df["action"] == "guess_invalid_word"]
    total = len(invalid_df)

    word_stats = (
        invalid_df.groupby("word")["user_id"]
        .nunique()
        .rename("distinct_users")
        .sort_values(ascending=False)
        .reset_index()
    )
    word_stats["count"] = invalid_df.groupby("word").size().reindex(word_stats["word"]).values
    word_stats["count/inv_%"] = (word_stats["count"] / total * 100).round(2)
    word_stats["cumulative_%"] = word_stats["count/inv_%"].cumsum().round(2)

    print(f"\n[ top {top_n} hangul invalid words by distinct users (total unique words: {len(word_stats):,}) ]")
    print(word_stats.head(top_n).to_string(index=False))

    coverage = word_stats.head(top_n)["count"].sum() / total * 100
    print(f"\ntop {top_n} words cover {coverage:.1f}% of all hangul invalid attempts")


def print_session_stats(df: pd.DataFrame):
    invalid_per_session = (
        df[df["action"] == "guess_invalid_word"]
        .groupby(["date", "user_id"])
        .size()
        .rename("invalid_count")
        .reset_index()
    )
    total_guess_per_session = (
        df[df["action"].isin(["guess", "guess_invalid_word"])]
        .groupby(["date", "user_id"])
        .size()
        .rename("total_guess_count")
        .reset_index()
    )
    give_up_sessions = (
        df[df["action"] == "give_up"]
        .groupby(["date", "user_id"])
        .size()
        .gt(0)
        .rename("gave_up")
        .reset_index()
    )
    sessions = (
        df.groupby(["date", "user_id"])
        .size()
        .rename("action_count")
        .reset_index()
        .merge(invalid_per_session, on=["date", "user_id"], how="left")
        .merge(total_guess_per_session, on=["date", "user_id"], how="left")
        .merge(give_up_sessions, on=["date", "user_id"], how="left")
    )
    sessions["invalid_count"] = sessions["invalid_count"].fillna(0).astype(int)
    sessions["total_guess_count"] = sessions["total_guess_count"].fillna(0).astype(int)
    sessions["gave_up"] = sessions["gave_up"].fillna(False)
    sessions["invalid_ratio"] = (
        sessions["invalid_count"] / sessions["total_guess_count"].replace(0, pd.NA)
    )

    def session_stats(g):
        has_invalid = g["invalid_count"] > 0
        return pd.Series({
            "total_sessions": len(g),
            "avg_invalid_ratio_%": round(g["invalid_ratio"].mean() * 100, 2),
            "giveup%(with_invalid)": round(g.loc[has_invalid, "gave_up"].mean() * 100, 2) if has_invalid.any() else None,
            "giveup%(no_invalid)": round(g.loc[~has_invalid, "gave_up"].mean() * 100, 2) if (~has_invalid).any() else None,
        })

    session_summary = sessions.groupby("date").apply(session_stats)

    print("\n[ session-level invalid & give-up by date ]")
    print(session_summary)

    bins = [-0.001, 0, 0.1, 0.2, 0.3, 0.5, 1.0]
    labels = ["0%", "1-10%", "11-20%", "21-30%", "31-50%", "51%+"]
    sessions["invalid_bin"] = pd.cut(sessions["invalid_ratio"].fillna(0), bins=bins, labels=labels)

    dist = (
        sessions.groupby("date")["invalid_bin"]
        .value_counts(normalize=True)
        .mul(100)
        .round(2)
        .unstack(fill_value=0)
    )
    print(f"\n[ invalid ratio distribution per session (%) by date ]")
    print(dist.to_string())


def print_outlier_sessions(df: pd.DataFrame, threshold: int = 21, sample_n: int = 5):
    invalid_per_session = (
        df[df["action"] == "guess_invalid_word"]
        .groupby(["date", "user_id"])
        .size()
        .rename("invalid_count")
        .reset_index()
    )
    outliers = invalid_per_session[invalid_per_session["invalid_count"] >= threshold]

    print(f"\n[ outlier sessions (invalid >= {threshold}): {len(outliers):,} sessions ]")
    print(outliers.groupby("date")["user_id"].count().rename("outlier_sessions"))

    invalid_df = df[df["action"] == "guess_invalid_word"]
    sample = outliers.sample(n=min(sample_n, len(outliers)), random_state=42)
    for _, row in sample.iterrows():
        words = (
            invalid_df[
                (invalid_df["date"] == row["date"]) &
                (invalid_df["user_id"] == row["user_id"])
            ]["word"]
            .value_counts()
        )
        print(f"\n  date={row['date']}  user={row['user_id']}  invalid_count={row['invalid_count']}")
        print(words.to_string())


def _build_user_retention(df: pd.DataFrame) -> pd.DataFrame:
    guess_df = df[df["action"].isin(["guess", "guess_invalid_word"])]
    user_total = guess_df.groupby("user_id").size().rename("total_guess")
    user_invalid = (
        df[df["action"] == "guess_invalid_word"]
        .groupby("user_id")
        .size()
        .rename("invalid_count")
    )
    user_dates = df.groupby("user_id")["date"].apply(set).rename("dates")

    users = pd.DataFrame({
        "total_guess": user_total,
        "invalid_count": user_invalid.reindex(user_total.index, fill_value=0),
        "dates": user_dates.reindex(user_total.index),
    })
    users["invalid_ratio"] = users["invalid_count"] / users["total_guess"]
    users["first_date"] = users["dates"].apply(min)

    sorted_dates = sorted(df["date"].unique())
    date_to_idx = {d: i for i, d in enumerate(sorted_dates)}

    for d in range(1, 4):
        col = f"D+{d}"
        users[col] = users.apply(
            lambda row, d=d: (
                sorted_dates[date_to_idx[row["first_date"]] + d] in row["dates"]
                if date_to_idx[row["first_date"]] + d < len(sorted_dates)
                else pd.NA
            ),
            axis=1,
        )

    bins = [-0.001, 0, 0.1, 0.2, 0.3, 0.5, 1.0]
    labels = ["0%", "1-10%", "11-20%", "21-30%", "31-50%", "51%+"]
    users["invalid_bin"] = pd.cut(users["invalid_ratio"], bins=bins, labels=labels)
    return users


def _retention_summary(users: pd.DataFrame) -> pd.DataFrame:
    retention_cols = ["D+1", "D+2", "D+3"]

    def agg(g):
        result = {"n": len(g)}
        for col in retention_cols:
            valid = g[col].dropna()
            result[f"{col}_%"] = round(valid.mean() * 100, 1) if len(valid) > 0 else None
            result[f"{col}_n"] = len(valid)
        return pd.Series(result)

    return users.groupby("invalid_bin").apply(agg)


def print_retention_by_invalid_ratio(df: pd.DataFrame):
    all_users = _build_user_retention(df)
    login_users = _build_user_retention(df[df["user_type"] == "user"])

    all_summary = _retention_summary(all_users)
    login_summary = _retention_summary(login_users)

    print(f"\n[ retention by invalid ratio — all users (n={len(all_users):,}) ]")
    print(all_summary.to_string())

    print(f"\n[ retention by invalid ratio — login users only (n={len(login_users):,}) ]")
    print(login_summary.to_string())


if __name__ == "__main__":
    zip_paths = glob.glob("data/game-event-logs/*.jsonl.zip")
    df = load_logs(zip_paths)

    invalid_df = prepare_invalid_df(df)
    print_date_summary(df, invalid_df)

    df_clean = drop_non_hangul_invalid(df)

    #print_session_stats(df_clean)
    #print_outlier_sessions(df_clean)
    #print_word_stats(df_clean, top_n=50)
    print_retention_by_invalid_ratio(df_clean)
