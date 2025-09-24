from airflow.providers.postgres.hooks.postgres import PostgresHook

from common.configs import INTERVAL_DAYS
from common.exceptions import DuplicateAnswerException


def upsert_answer(pg_hook: PostgresHook, date: str, ans_id: int):
    upserted_row = pg_hook.get_first(
        sql="""
        INSERT INTO answer (date, word_id)
        SELECT %(date)s, %(word_id)s
        WHERE NOT EXISTS (
            SELECT 1
            FROM answer
            WHERE word_id = %(word_id)s
            AND date != %(date)s
            AND date BETWEEN NOW() - INTERVAL %(interval_days)s AND NOW() + INTERVAL %(interval_days)s 
        )
        ON CONFLICT (date) DO UPDATE
        SET word_id = excluded.word_id
        RETURNING *;
        """,
        parameters={"date": date, "word_id": ans_id, "interval_days": f"{INTERVAL_DAYS} days"}
    )
    if not upserted_row:
        raise DuplicateAnswerException(f"There is duplicated answer between {INTERVAL_DAYS} days")