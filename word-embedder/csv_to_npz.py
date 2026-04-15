"""Convert embedding CSV to npz format.

CSV schema: word (str), emb (stringified Python list)
npz schema: words (N,), embeddings (N, D)

Usage:
    python csv_to_npz.py --input data/embedding/init.csv --output data/embedding/init.npz
"""

import argparse
import ast
import csv

import numpy as np


def convert(csv_path: str, npz_path: str):
    if not csv_path.endswith(".csv"):
        raise ValueError(f"Input file must be a CSV: {csv_path}")
    if not npz_path.endswith(".npz"):
        raise ValueError(f"Output file must be .npz: {npz_path}")

    words = []
    embeddings = []

    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            words.append(row["word"])
            embeddings.append(ast.literal_eval(row["emb"]))

    print("csv load completed !!")

    np.savez_compressed(
        npz_path,
        words=np.array(words),
        embeddings=np.array(embeddings, dtype=np.float32),
    )
    print(f"Converted {len(words)} entries: {csv_path} -> {npz_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=str, required=True, help="Path to input CSV file")
    parser.add_argument("--output", type=str, required=True, help="Path to output npz file")
    args = parser.parse_args()

    convert(args.input, args.output)
