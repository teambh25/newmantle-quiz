import json
import os

from airflow.decorators import dag, task
from airflow.exceptions import AirflowException
from airflow.models.param import Param
from airflow.providers.http.hooks.http import HttpHook
from airflow.providers.postgres.hooks.postgres import PostgresHook
from quiz_pipeline.quiz import Quiz

import common.crud as crud
import common.exceptions as exc


@dag(
    dag_id="register_quiz",
    schedule_interval=None,
    params={
        "date": Param(
            type="string",
            title="Date",
            description="Quiz registration date (YYYY-MM-DD)",
        ),
    },
    tags=["admin", "trigger"],
)
def quiz_register():
    @task
    def generate_quiz_and_save(params: dict):
        date = params["date"]
        pg_hook = PostgresHook(postgres_conn_id="quiz_db")

        try:
            word_id, word, tag, description = crud.fetch_answer_by_date(pg_hook, date)
        except exc.NotFoundInDB as e:
            raise AirflowException(e.msg)

        dists = crud.calc_cos_dists(pg_hook, word_id)
        print(f"# words : {len(dists)}")

        quiz = Quiz(date, word, tag, description, dists)
        quiz_file_path = quiz.save()
        return quiz_file_path

    @task
    def upload_quiz(quiz_file_path: str):
        try:
            with open(quiz_file_path, "r") as quiz_file:
                quiz = json.load(quiz_file)
            print(f"check | {quiz["answer"]} {quiz["date"]} {len(quiz["scores"])}")
            http_hook = HttpHook(method="PUT", http_conn_id="game_server")
            response = http_hook.run(
                endpoint="/admin/quizzes",
                json=quiz,
            )  # will raise AirflowException on bad response
            print(response.json())
        finally:
            os.remove(quiz_file_path)
            print("delete quiz file!")


    quiz_file_path = generate_quiz_and_save()
    upload_quiz(quiz_file_path)

quiz_register()
