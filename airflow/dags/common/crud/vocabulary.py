from airflow.providers.postgres.hooks.postgres import PostgresHook

from common.exceptions import NotFoundInDB


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