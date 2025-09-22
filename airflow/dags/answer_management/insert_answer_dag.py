from airflow.decorators import dag 
from airflow.models.param import Param

from common.tasks import get_id_by_word_in_vocab, insert_answer


@dag(
    dag_id="insert_answer",
    schedule_interval=None,
    params={
        "date": Param(type="string",title="update date",description="update date in YYYY-MM-DD format"),
        "answer": Param(type="string",title="anwer word",description="hangul word"),
    },
)
def insert_answer_dag():
    answer = "{{ params.answer }}"
    date = "{{ params.date }}"
    ans_id = get_id_by_word_in_vocab(answer)
    insert_answer(date, ans_id)

insert_answer_dag()