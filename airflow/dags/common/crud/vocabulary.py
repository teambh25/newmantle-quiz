from airflow.providers.postgres.hooks.postgres import PostgresHook

from common.exceptions import NotFoundInDB


def calc_cos_dists(pg_hook: PostgresHook, word_id: str) -> tuple:
    dists = pg_hook.get_records(
        sql="""
                SELECT word, 1 - (emb <=> (SELECT emb FROM vocabulary WHERE id=%(word_id)s)) as dist
                FROM vocabulary
                WHERE id != %(word_id)s
                """,
        parameters={"word_id": word_id},
    )
    return dists


def get_id_by_word_in_vocab(pg_hook: PostgresHook, word: str) -> int:
    word_id = pg_hook.get_first(
        sql="""
        SELECT id
        FROM  vocabulary
        WHERE word = %(word)s
        """,
        parameters={"word": word},
    )
    if word_id is None:
        raise NotFoundInDB(f"There is no {word} in vocabulary")
    return word_id[0]


if __name__ == "__main__":
    pg_hook = PostgresHook(postgres_conn_id="quiz_db")
    print(calc_cos_dists(pg_hook, 36911))
