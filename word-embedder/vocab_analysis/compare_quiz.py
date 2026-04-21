"""
Compare quiz top-K scores for a given word across two vocabulary tables.

Usage (run from word-embedder/ directory):
    python analysis/compare_quiz.py --word 태권도
    python analysis/compare_quiz.py --word 태권도 --old_table vocabulary_old --new_table vocabulary --top_k 50
    python analysis/compare_quiz.py --word 태권도 --csv
"""

import argparse
import os
import sys

import pandas as pd
import psycopg
from dotenv import load_dotenv
from pgvector.psycopg import register_vector

sys.path.append(".")
load_dotenv()

pd.set_option("display.unicode.east_asian_width", True)
pd.set_option("display.max_rows", None)
pd.set_option("display.max_colwidth", 20)


# ── DB ────────────────────────────────────────────────────────────────────────

def _get_conn() -> psycopg.Connection:
    conn = psycopg.connect(
        host=os.environ["DB_HOST"],
        port=int(os.environ.get("DB_PORT", 5432)),
        dbname=os.environ["DB_NAME"],
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
    )
    register_vector(conn)
    return conn


# ── Query ─────────────────────────────────────────────────────────────────────

def _fetch_word_id(cur: psycopg.Cursor, table: str, word: str) -> int:
    cur.execute(f"SELECT id FROM {table} WHERE word = %s", (word,))
    row = cur.fetchone()
    if row is None:
        raise ValueError(f"'{word}' not found in table '{table}'")
    return row[0]


def _calc_scores(cur: psycopg.Cursor, table: str, word_id: int) -> dict[str, float]:
    """Return {word: score} for all words in the table except the target word.

    Replicates Quiz.cal_scores():
        score = (dist - min_dist) / (1 - min_dist) * 100
    where dist = cosine similarity (1 - cosine distance), higher = more similar.
    """
    cur.execute(
        f"""
        SELECT word, 1 - (emb <=> (SELECT emb FROM {table} WHERE id = %s)) AS dist
        FROM {table}
        WHERE id != %s
        """,
        (word_id, word_id),
    )
    rows = cur.fetchall()
    if not rows:
        return {}

    min_dist = min(dist for _, dist in rows)
    return {
        word: round((dist - min_dist) / (1 - min_dist) * 100, 2)
        for word, dist in rows
    }


def fetch_scores(word: str, table: str) -> dict[str, float]:
    with _get_conn() as conn:
        with conn.cursor() as cur:
            word_id = _fetch_word_id(cur, table, word)
            return _calc_scores(cur, table, word_id)


# ── Compare ───────────────────────────────────────────────────────────────────

def _top_k(scores: dict[str, float], k: int) -> list[tuple[str, float]]:
    return sorted(scores.items(), key=lambda x: x[1], reverse=True)[:k]


def build_comparison(
    old_scores: dict[str, float],
    new_scores: dict[str, float],
    old_table: str,
    new_table: str,
    top_k: int,
) -> tuple[pd.DataFrame, dict]:
    old_top = _top_k(old_scores, top_k)
    new_top = _top_k(new_scores, top_k)

    old_words = {w for w, _ in old_top}
    new_words = {w for w, _ in new_top}

    only_in_old = old_words - new_words
    only_in_new = new_words - old_words
    common = old_words & new_words

    # rank of each word in old_top (for computing rank change shown in new column)
    old_rank = {w: i + 1 for i, (w, _) in enumerate(old_top)}

    rows = []
    for rank, ((old_w, old_s), (new_w, new_s)) in enumerate(zip(old_top, new_top), start=1):
        if new_w in only_in_new:
            new_w_label = f"{new_w} (new)"
        else:
            delta = old_rank[new_w] - rank  # positive = moved up in new_table
            sign = "+" if delta > 0 else ""
            new_w_label = f"{new_w} ({sign}{delta})" if delta != 0 else new_w

        rows.append(
            {
                "rank": rank,
                f"{old_table}_word": f"{old_w} (removed)" if old_w in only_in_old else old_w,
                f"{old_table}_score": old_s,
                f"{new_table}_word": new_w_label,
                f"{new_table}_score": new_s,
            }
        )

    df_side = pd.DataFrame(rows)

    summary = {
        "vocab_size": {old_table: len(old_scores), new_table: len(new_scores)},
        "top_k": top_k,
        "common_in_top_k": len(common),
    }

    return df_side, summary


# ── Output ────────────────────────────────────────────────────────────────────

def _print_summary(word: str, old_table: str, new_table: str, summary: dict):
    v = summary["vocab_size"]
    print(f"\n{'':=<60}")
    print(f"  word    : {word}")
    print(f"  top_k   : {summary['top_k']}")
    print(f"  {old_table} vocab : {v[old_table]:,}")
    print(f"  {new_table} vocab : {v[new_table]:,}")
    print(f"  common in top-{summary['top_k']} : {summary['common_in_top_k']}")
    print(f"{'':=<60}")


def print_results(
    word: str,
    old_table: str,
    new_table: str,
    df_side: pd.DataFrame,
    summary: dict,
):
    _print_summary(word, old_table, new_table, summary)

    print(f"\n── Top-{summary['top_k']} side-by-side ──")
    print(df_side.to_string(index=False))


def save_csv(word: str, old_table: str, new_table: str, df_side: pd.DataFrame):
    path = f"data/analysis/compare_{word}_{old_table}_vs_{new_table}.csv"

    os.makedirs("data/analysis", exist_ok=True)
    df_side.to_csv(path, index=False, encoding="utf-8-sig")
    print(f"\n[saved] {path}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Compare quiz top-K for a word across two vocab tables")
    parser.add_argument("--word", required=True, help="Target answer word")
    parser.add_argument("--old_table", default="vocabulary_old", help="Old vocabulary table (default: vocabulary_old)")
    parser.add_argument("--new_table", default="vocabulary", help="New vocabulary table (default: vocabulary)")
    parser.add_argument("--top_k", type=int, default=30, help="Number of top words to compare (default: 30)")
    parser.add_argument("--csv", action="store_true", help="Save results to CSV under data/analysis/")
    args = parser.parse_args()

    print(f"Fetching scores from '{args.old_table}'...")
    old_scores = fetch_scores(args.word, args.old_table)

    print(f"Fetching scores from '{args.new_table}'...")
    new_scores = fetch_scores(args.word, args.new_table)

    df_side, summary = build_comparison(
        old_scores, new_scores, args.old_table, args.new_table, args.top_k
    )

    print_results(args.word, args.old_table, args.new_table, df_side, summary)

    if args.csv:
        save_csv(args.word, args.old_table, args.new_table, df_side)


if __name__ == "__main__":
    main()
