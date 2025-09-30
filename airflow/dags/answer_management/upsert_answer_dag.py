from airflow.datasets.metadata import Metadata
from airflow.decorators import dag, task
from airflow.exceptions import AirflowException
from airflow.models.param import Param
from airflow.providers.postgres.hooks.postgres import PostgresHook

import common.crud as crud
import common.datasets as datasets
import common.exceptions as exc


@dag(
    dag_id="upsert_answer",
    schedule=None,
    params={
        "word": Param(
            type="string", title="anwer word", description="hangul answer word"
        ),
        "date": Param(
            type="string",
            title="update date",
            description="update date in YYYY-MM-DD format",
        ),
        "description": Param(
            type="string",
            title="anwer description",
            description="short description of the answer",
            default="임의의로 뽑은 단어입니다.",
        ),
        "tag": Param(
            type="string",
            title="anwer tag",
            description="tag for the answer",
            default="랜덤",
        ),
    },
    tags=["admin", "producer"],
)
def upsert_answer():
    @task
    def upsert_answer(params: dict):
        pg_hook = PostgresHook(postgres_conn_id="quiz_db")
        try:
            word_id = crud.get_id_by_word_in_vocab(pg_hook, params["word"])
            crud.upsert_answer(
                pg_hook, params["date"], word_id, params["tag"], params["description"]
            )
        except exc.NotFoundInDB as e:
            raise AirflowException(e.msg)
        except exc.DuplicateAnswerException as e:
            raise AirflowException(e.msg)
        return params["date"]

    @task(outlets=[datasets.answer_dataset])
    def produce_quiz_date(dates: str):
        print(f"updated date: {dates}")
        yield Metadata(datasets.answer_dataset, {"changed_answer_dates": [dates]})

    updated_date = upsert_answer()
    produce_quiz_date(updated_date)


upsert_answer()
