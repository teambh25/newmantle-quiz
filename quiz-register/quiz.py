import datetime
from typing import Tuple, Dict

import psycopg
from loguru import logger

from config import Configs


class Quiz:
    def __init__(self, configs: Configs, date: datetime.date, answer: str):
        url = f"postgresql://{configs.db_user}:{configs.db_pw}@postgres:5432/{configs.db_name}"
        self.db_conn = psycopg.connect(url, autocommit=True)
        self.date: str = f"{date}"
        self.answer: str = answer
        self.scores = self.calc_similarity_scores(answer)
    
    def calc_similarity_scores(self, answer) -> Dict[str, float]:
        dists = self.fetch_all_cos_dist(answer)
        min_dist = min(dists, key=lambda x:x[1])[1]
        max_dist = max(dists, key=lambda x:x[1])[1]
        scores = {
            word: Quiz._scale_to_percentage(dist, min=min_dist, max=max_dist) \
            for word, dist in dists
        }
        del scores[answer]
        return scores
            
    def fetch_all_cos_dist(self, target_word: str) -> Tuple[str, float]:
        query = f"\
            SELECT word, 1 - (emb <=> (SELECT emb word FROM vocabulary WHERE word='{target_word}'))\
            FROM vocabulary\
        "
        return self.db_conn.execute(query).fetchall()

    @staticmethod
    def _scale_to_percentage(x: float, min: float, max: float) -> float:
        ''' min-max scaling for '''
        return round((x-min) / (max-min) * 100, 2)
    
    def to_dict(self):
        return {"date": self.date, "answer": self.answer, "scores": self.scores}