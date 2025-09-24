from datetime import datetime, timedelta

from airflow.decorators import dag, task
from airflow.models.param import Param
from airflow.providers.postgres.hooks.postgres import PostgresHook


@dag(
    dag_id="print_answers",
    schedule_interval=None,
    params={
        "date": Param(
            type="string",
            title="start date",
            description="start date in YYYY-MM-DD format",
        ),
        "days": Param(
            7,
            type="integer",
            title="days",
            description="number of consecutive days to print",
        ),
    },
    tags=["admin", "trigger"],
)
def print_answers():
    @task
    def print_anwers(params: dict):
        start_date = datetime.strptime(params["date"], "%Y-%m-%d").date()
        end_date = start_date + timedelta(days=params["days"] - 1)

        pg_hook = PostgresHook(postgres_conn_id="quiz_db")
        answers = pg_hook.get_records(
            sql="""
            SELECT a.date, v.word, v.id
            FROM answer a
            INNER JOIN vocabulary v ON a.word_id = v.id
            WHERE a.date BETWEEN %(start_date)s AND %(end_date)s
            """,
            parameters={"start_date": start_date, "end_date": end_date},
        )
        print(answers)

    print_anwers()


print_answers()
