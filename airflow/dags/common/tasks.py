from airflow.decorators import task
from airflow.exceptions import AirflowException
from airflow.providers.postgres.hooks.postgres import PostgresHook

from common.configs import INTERVAL_DAYS


@task
def get_id_by_word_in_vocab(word: str) -> int:
    pg_hook = PostgresHook(postgres_conn_id="quiz_db")
    word_id = pg_hook.get_first(
        sql="""
        SELECT id
        FROM  vocabulary
        WHERE word = %(word)s
        """,
        parameters={"word": word},
    )
    if word_id is None:
        raise AirflowException(f"There is no {word} in vocabulary")
    return word_id[0]


@task
def insert_answer(date: str, ans_id: int):
    pg_hook = PostgresHook(postgres_conn_id="quiz_db")
    inserted_row = pg_hook.get_first(
        sql="""
        INSERT INTO answer (date, word_id)
        SELECT %(date)s, %(word_id)s
        WHERE NOT EXISTS (
            SELECT 1
            FROM answer
            WHERE word_id = %(word_id)s
            AND date BETWEEN NOW() - INTERVAL %(interval_days)s AND NOW() + INTERVAL %(interval_days)s 
        )
        RETURNING *;
        """,
        parameters={
            "date": date,
            "word_id": ans_id,
            "interval_days": f"{INTERVAL_DAYS} days",
        },
    )
    if inserted_row:
        print(f"insert answer : {inserted_row}")
    else:
        raise AirflowException(
            f"There is duplicated answer between {INTERVAL_DAYS} days"
        )
