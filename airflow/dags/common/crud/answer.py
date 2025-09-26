from airflow.providers.postgres.hooks.postgres import PostgresHook

from common.configs import INTERVAL_DAYS
import common.exceptions as exc
import common.utils as utils

def upsert_answer(
    pg_hook: PostgresHook, date: str, word_id: int, tag: str, description: str
):
    '''
    Check for duplicate past answers only (exclude future answers)
    '''
    upserted_row = pg_hook.get_first(
        sql="""
            INSERT INTO answer (date, word_id, tag, description)
            SELECT %(date)s, %(word_id)s, %(tag)s, %(description)s
            WHERE NOT EXISTS (
                SELECT 1
                FROM answer
                WHERE word_id = %(word_id)s
                AND date >= %(window_start)s
                AND date < %(date)s
            )
            ON CONFLICT (date) DO UPDATE
            SET 
                word_id = excluded.word_id, 
                tag = excluded.tag,
                description = excluded.description
            RETURNING *;
        """,
        parameters={
            "date": date,
            "word_id": word_id,
            "tag": tag,
            "description": description,
            "window_start": utils.subtract_days(date, INTERVAL_DAYS),
        },
    )
    if not upserted_row:
        raise exc.DuplicateAnswerException("There is duplicated answer")


if __name__ == "__main__":
    # for test
    pg_hook = PostgresHook(postgres_conn_id="quiz_db")
    upsert_answer(pg_hook, "2025-09-28", 457, "random", "...")
