from airflow.decorators import dag 

from common.tasks import get_id_by_word_in_vocab, insert_answer

init_answers = [
    # ("2025-09-03", "인증"),
    # ("2025-09-04", "경로당"),
    # ("2025-09-05", "밝기"),
    # ("2025-09-06", "순대"),
    # ("2025-09-07", "잔여"),
    # ("2025-09-08", "안대"),
    # ("2025-09-09", "검찰청"),
    # ("2025-09-10", "월식"),
    # ("2025-09-11", "소액"),
    # ("2025-09-12", "훈련소"),
    # ("2025-09-13", "고점"),
    # ("2025-09-14", "맞벌이"),
    # ("2025-09-15", "발매"),
    # ("2025-09-16", "소나기"),
    # ("2025-09-17", "해킹"),
    # ("2025-09-18", "신인"),
    # ("2025-09-19", "수수료"),
]


@dag(
    dag_id="insert_init_answers",
    schedule_interval=None,
)
def insert_init_answers():
    for date, answer in init_answers:
        ans_id = get_id_by_word_in_vocab(answer)
        insert_answer(date, ans_id)

insert_init_answers()