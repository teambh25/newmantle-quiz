from airflow.datasets.metadata import Metadata
from airflow.decorators import dag, task
from airflow.models.param import Param

import common.datasets as datasets


@dag(
    dag_id="quiz_register_producer",
    schedule=None,
    params={
        "date": Param(
            type="string",
            title="Date",
            description="Quiz registration date (YYYY-MM-DD)",
        ),
    },
    tags=["admin", "producer"],
)
def producer():
    @task(outlets=[datasets.answer_dataset])
    def produce_quiz_date(params: dict):
        print(params["date"])
        yield Metadata(
            datasets.answer_dataset, {"changed_answer_dates": [params["date"]]}
        )

    produce_quiz_date()


producer()
