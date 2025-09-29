import pendulum

from airflow.decorators import dag, task

import common.configs as configs
from quiz_pipeline.quiz_task import generate_quiz_and_save, upload_quiz

@dag(
    dag_id="register_quizzes",
    schedule_interval=None,
    tags=["external_trigger"],
)
def register_quizzes():
    @task
    def generate_date_list(**context) -> list[str]:
        start_date = context["dag_run"].conf["start_date"]
        base_date = pendulum.parse(start_date)
        return [(base_date.add(days=i)).to_date_string() for i in range(3)] # configs.BATCH_SIZE

    dates = generate_date_list()
    quiz_file_paths = generate_quiz_and_save.expand(date=dates)
    upload_quiz.expand(quiz_file_path=quiz_file_paths)

register_quizzes()