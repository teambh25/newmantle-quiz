from airflow.providers.postgres.hooks.postgres import PostgresHook


def fetch_answer_details(pg_hook: PostgresHook, start_date: str, end_date: str):
    ans = pg_hook.get_records(
        sql="""
        SELECT a.date, v.word, a.tag, a.description
        FROM answer a
        INNER JOIN vocabulary v ON a.word_id = v.id
        WHERE a.date BETWEEN %(start_date)s AND %(end_date)s
        ORDER BY a.date
        """,
        parameters={"start_date": start_date, "end_date": end_date},
    )
    return ans
