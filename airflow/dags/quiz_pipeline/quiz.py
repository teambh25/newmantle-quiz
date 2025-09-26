import json
import tempfile
from typing import Dict, List, Tuple


class Quiz:
    def __init__(self, date: str, word: str, tag: str, description: str, dists: List[Tuple[str, float]]):
        self.date = date
        self.answer = word
        self.tag = tag
        self.description = description
        self.scores: Dict[str, float] = self.cal_scores(dists)

    @staticmethod
    def scaler_factory(min_dist: float):
        def scaler(x: float) -> float:
            """
            1. Min-Max Scaling: scale x from range [min_dist, max_dist] to [0, 1]
            2. Convert the [0, 1] range to [0, 100]
            """
            x = (x - min_dist) / (1 - min_dist)  # assume max_dist = 1 (answer)
            return round(x * 100, 2)

        return scaler

    def cal_scores(self, dists: List[Tuple[str, float]]):
        """Generate scores dictionary from (word, dist) list."""
        min_dist = min(dists, key=lambda x: x[1])[1]
        scaler = Quiz.scaler_factory(min_dist=min_dist)
        return {word: scaler(dist) for word, dist in dists}

    def to_dict(self) -> Dict:
        return {
            "date": self.date,
            "answer": self.answer,
            # "tag": self.tag,
            # "description": self.description,
            "scores": self.scores,
        }

    def save(self) -> str:
        """Save quiz as JSON to a temporary file. Returns file path."""
        with tempfile.NamedTemporaryFile(
            mode="w", delete=False, prefix="quiz_", suffix=".json"
        ) as quiz_file:
            json.dump(self.to_dict(), quiz_file)
            print(f"Saved quiz file : {quiz_file.name}")
            return quiz_file.name