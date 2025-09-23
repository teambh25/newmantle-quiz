import os
import json
import tempfile
from datetime import datetime, timedelta

from airflow.decorators import dag, task
from airflow.exceptions import AirflowException
from airflow.models.param import Param
from airflow.providers.http.hooks.http import HttpHook
from airflow.providers.postgres.hooks.postgres import PostgresHook


@dag(
    dag_id="quiz_register_dag",
    schedule_interval=None,
    params={
        "date": Param(type="string",title="Date",description="Quiz registration date (YYYY-MM-DD)"),
    },
    tags=["admin", "trigger"]
)
def quiz_register():

    @task
    def get_answer_by_date(params: dict) -> str:
        date = params["date"]
        pg_hook = PostgresHook(postgres_conn_id="quiz_db")
        ans = pg_hook.get_first(
            sql="""
                SELECT word
                FROM vocabulary
                WHERE id = (
                        SELECT word_id
                        FROM  answer
                        WHERE date = %(date)s
                    )
            """,
            parameters={"date": date},
        )
        if ans is None:
            raise AirflowException(f"There is no {date}'s answer")
        return ans[0]


    @task
    def generate_quiz_and_save(ans: str, params: dict):
        date = params["date"]
        pg_hook = PostgresHook(postgres_conn_id="quiz_db")
        dists = pg_hook.get_records(
            sql = """
                SELECT word, 1 - (emb <=> (SELECT emb FROM vocabulary WHERE word=%(ans)s))
                FROM vocabulary
                WHERE word != %(ans)s
                """,
            parameters={"ans": ans},
        )

        min_dist = min(dists, key=lambda x:x[1])[1]
        scale_to_percentage = lambda x: round((x-min_dist) / (1 - min_dist) * 100, 2)  # answer is dist 1
        scores = {word: scale_to_percentage(dist) for word, dist in dists}
        print(f"#words : {len(scores)}")
        quiz = {"date": date, "answer": ans, "scores": scores}

        with tempfile.NamedTemporaryFile(mode='w', delete=False, prefix=f"quiz_", suffix=".json") as quiz_file:
            json.dump(quiz, quiz_file)
            print("save quiz file!")
        return quiz_file.name

        
    @task
    def upload_quiz(quiz_file_path: str):
        try:
            with open(quiz_file_path, "r") as quiz_file:
                quiz = json.load(quiz_file)
    
            http_hook = HttpHook(method="PUT",  http_conn_id="game_server")
            response = http_hook.run(
                endpoint="/admin/quizzes",
                json = quiz,
            )  # will raise AirflowException on bad response
            print(response.json())
        finally:
            os.remove(quiz_file_path)
            print("delete quiz file!")
    

    ans = get_answer_by_date()
    quiz_file_path = generate_quiz_and_save(ans)
    upload_quiz(quiz_file_path)

quiz_register()