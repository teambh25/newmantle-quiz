from airflow.decorators import dag, task
from airflow.exceptions import AirflowException
from airflow.models.param import Param
from airflow.providers.postgres.hooks.postgres import PostgresHook
from common.configs import INTERVAL_DAYS
from common.tasks import get_id_by_word_in_vocab


@dag(
    dag_id="update_answer",
    schedule_interval=None,
    params={
        "date": Param(
            type="string",
            title="update date",
            description="update date in YYYY-MM-DD format",
        ),
        "answer": Param(type="string", title="anwer word", description="hangul word"),
    },
    tags=["admin", "trigger"],
)
def update_answer():
    @task
    def get_params(params: dict) -> dict:
        return params

    @task
    def update_answer(date: str, ans_id: int):
        pg_hook = PostgresHook(postgres_conn_id="quiz_db")
        updated_row = pg_hook.get_first(
            sql="""
            UPDATE answer a
            SET date = %(date)s, word_id = %(word_id)s
            WHERE a.date = %(date)s
            AND NOT EXISTS (
                SELECT 1
                FROM answer
                WHERE date != %(date)s
                AND word_id = %(word_id)s
                AND date BETWEEN NOW() - INTERVAL %(interval_days)s AND NOW() + INTERVAL %(interval_days)s
            )
            RETURNING *;
            """,
            parameters={
                "date": f"{date}",
                "word_id": ans_id,
                "interval_days": f"{INTERVAL_DAYS} days",
            },
        )
        if updated_row:
            print(f"update answer : {updated_row}")
        else:
            raise AirflowException(
                f"There is duplicated answer between {INTERVAL_DAYS} days"
            )

    params = get_params()
    ans_id = get_id_by_word_in_vocab(params["answer"])
    update_answer(params["date"], ans_id)


update_answer()
