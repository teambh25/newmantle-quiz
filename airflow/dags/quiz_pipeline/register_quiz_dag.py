from airflow.decorators import dag
from airflow.models.param import Param
from quiz_pipeline.quiz_task import generate_quiz_and_save, upload_quiz

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
    date = "{{ params.date }}"
    quiz_file_path = generate_quiz_and_save(date)
    upload_quiz(quiz_file_path)

quiz_register()
