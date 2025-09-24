from airflow.providers.postgres.hooks.postgres import PostgresHook
from common.configs import INTERVAL_DAYS
from common.exceptions import DuplicateAnswerException


def upsert_answer(
    pg_hook: PostgresHook, date: str, word_id: int, tag: str, description: str
):
    upserted_row = pg_hook.get_first(
        sql="""
            INSERT INTO answer (date, word_id, tag, description)
            SELECT %(date)s, %(word_id)s, %(tag)s, %(description)s
            WHERE NOT EXISTS (
                SELECT 1
                FROM answer
                WHERE word_id = %(word_id)s
                AND date != %(date)s
                AND date BETWEEN NOW() - INTERVAL %(interval_days)s AND NOW() + INTERVAL %(interval_days)s 
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
            "interval_days": f"{INTERVAL_DAYS} days",
        },
    )
    if not upserted_row:
        raise DuplicateAnswerException("There is duplicated answer")


if __name__ == "__main__":
    # for test
    pg_hook = PostgresHook(postgres_conn_id="quiz_db")
    upsert_answer(pg_hook, "2025-09-25", 456, "태2", "아무2")
