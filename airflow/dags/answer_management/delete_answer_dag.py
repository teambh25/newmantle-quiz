from airflow.decorators import dag, task
from airflow.exceptions import AirflowException
from airflow.models.param import Param
from airflow.providers.postgres.hooks.postgres import PostgresHook


@dag(
    dag_id="delete_answer",
    schedule_interval=None,
    params={
        "date": Param(
            type="string",
            title="update date",
            description="update date in YYYY-MM-DD format",
        ),
    },
    tags=["admin", "trigger"],
)
def delete_answer():
    @task
    def delete_answer(params: dict):
        pg_hook = PostgresHook(postgres_conn_id="quiz_db")
        deleted_row = pg_hook.get_first(
            sql="""
            DELETE
            FROM answer
            WHERE date = %(date)s
            RETURNING *;
            """,
            parameters={"date": params["date"]},
        )
        if deleted_row:
            print(f"delete answer : {deleted_row}")
        else:
            raise AirflowException(f"There is no answer on {params['date']}")

    delete_answer()


delete_answer()
