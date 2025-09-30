import os

from airflow.decorators import dag, task, task_group
from airflow.exceptions import AirflowException
from airflow.providers.http.hooks.http import HttpHook
from airflow.providers.postgres.hooks.postgres import PostgresHook
from airflow.utils.dates import days_ago

import common.crud as crud
import common.datasets as datasets
import common.exceptions as exc
import common.utils as utils
from quiz_pipeline.quiz import Quiz


@dag(
    dag_id="quiz_register_consumer",
    start_date=days_ago(1),
    schedule=[datasets.answer_dataset],
    catchup=False,
    tags=["consumer"],
)
def register_quizzes():
    @task(inlets=[datasets.answer_dataset])
    def get_changed_answer_dates(inlet_events) -> list:
        last_events = inlet_events[datasets.answer_dataset][-1]
        return last_events.extra["changed_answer_dates"]

    @task_group
    def generate_and_upload_quizzes(date: str):
        @task
        def generate_quiz_and_save(date: str):
            pg_hook = PostgresHook(postgres_conn_id="quiz_db")

            try:
                word_id, word, tag, description = crud.fetch_answer_by_date(
                    pg_hook, date
                )
            except exc.NotFoundInDB as e:
                raise AirflowException(e.msg)

            dists = crud.calc_cos_dists(pg_hook, word_id)
            quiz = Quiz(date, word, tag, description, dists)

            quiz_file_path = utils.save_temp_json(quiz.to_dict(), prefix="quiz_")
            return quiz_file_path

        @task(pool="game_api_rate_limit")
        def upload_quiz(quiz_file_path: str):
            try:
                quiz = utils.load_json(quiz_file_path)
                print(
                    f"check | {quiz['date']}: {quiz['answer']}, # scores : {len(quiz['scores'])}"
                )
                http_hook = HttpHook(method="PUT", http_conn_id="game_server")
                response = http_hook.run(
                    endpoint="/admin/quizzes",
                    json=quiz,
                )  # will raise AirflowException on bad response
                print(response.json())
            finally:
                os.remove(quiz_file_path)
                print("delete quiz file!")

        quiz_file_path = generate_quiz_and_save(date)
        upload_quiz(quiz_file_path)

    changed_answer_dates = get_changed_answer_dates()
    generate_and_upload_quizzes.expand(date=changed_answer_dates)


register_quizzes()
