import os
from datetime import timedelta

from airflow.decorators import dag, task, task_group
from airflow.exceptions import AirflowException, AirflowFailException
from airflow.providers.http.hooks.http import HttpHook
from airflow.providers.postgres.hooks.postgres import PostgresHook
from airflow.utils.dates import days_ago

import common.crud as crud
import common.datasets as datasets
import common.exceptions as exc
import common.notifications as notifications
import common.utils as utils
from quiz_generation.quiz import Quiz


@dag(
    dag_id="quiz_register_consumer",
    start_date=days_ago(1),
    schedule=[datasets.answer_dataset],
    catchup=False,
    default_args={"on_failure_callback": notifications.notify_failure},
    tags=["consumer"],
)
def register_quizzes():
    @task(inlets=[datasets.answer_dataset])
    def get_changed_answer_dates(inlet_events) -> list:
        last_events = inlet_events[datasets.answer_dataset][-1]
        return last_events.extra["changed_answer_dates"]

    @task_group()
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

        @task(pool="game_api_rate_limit", retries=2, retry_delay=timedelta(minutes=1))
        def upload_quiz(quiz_file_path: str):
            quiz = utils.load_json(quiz_file_path)
            print(
                f"check | {quiz['date']}: {quiz['answer']}, # scores : {len(quiz['scores'])}"
            )
            http_hook = HttpHook(method="PUT", http_conn_id="game_server")
            response = http_hook.run(
                endpoint="/admin/quizzes",
                json=quiz,
                extra_options={"check_response": False},
            )
            if response.status_code >= 500:
                raise AirflowException(f"server error {response.status_code}: {response.text}")
            if not response.ok:
                raise AirflowFailException(f"client error {response.status_code}: {response.text}")
            print(response.json())

        @task(trigger_rule="all_done")
        def cleanup_quiz_file(quiz_file_path: str):
            if os.path.exists(quiz_file_path):
                os.remove(quiz_file_path)
                print("delete quiz file!")

        quiz_file_path = generate_quiz_and_save(date)
        upload_task = upload_quiz(quiz_file_path)
        cleanup_task = cleanup_quiz_file(quiz_file_path)
        upload_task >> cleanup_task

    changed_answer_dates = get_changed_answer_dates()
    generate_and_upload_quizzes.expand(date=changed_answer_dates)


register_quizzes()
