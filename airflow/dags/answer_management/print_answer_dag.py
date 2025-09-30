from pprint import pprint

from airflow.decorators import dag, task
from airflow.models.param import Param
from airflow.providers.postgres.hooks.postgres import PostgresHook

import common.crud as crud
import common.utils as utils


@dag(
    dag_id="print_answers",
    schedule=None,
    params={
        "date": Param(
            type="string",
            title="start date",
            description="start date in YYYY-MM-DD format",
        ),
        "days": Param(
            type="integer",
            title="days",
            description="number of consecutive days to print",
            default=7,
        ),
    },
    tags=["admin"],
)
def print_answers():
    @task
    def print_anwers(params: dict):
        start_date = params["date"]
        end_date = utils.add_days(start_date, params["days"] - 1)

        pg_hook = PostgresHook(postgres_conn_id="quiz_db")
        answers = crud.fetch_answer_details(pg_hook, start_date, end_date)
        pprint(answers)

    print_anwers()


print_answers()
