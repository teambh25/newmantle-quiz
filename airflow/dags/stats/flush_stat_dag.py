from datetime import timedelta

import pendulum
from airflow.decorators import dag, task
from airflow.providers.http.hooks.http import HttpHook

import common.notifications as notifications


@dag(
    dag_id="flush_stat",
    start_date=pendulum.datetime(2026, 4, 13, tz="Asia/Seoul"),
    schedule="30 17 * * *",
    catchup=False,
    default_args={"on_failure_callback": notifications.notify_failure},
    tags=["schedule", "stats"],
)
def flush_stat():
    @task
    def get_flush_dates(data_interval_end: pendulum.DateTime) -> list[str]:
        end = data_interval_end.in_timezone("Asia/Seoul")
        return [(end - timedelta(days=i)).to_date_string() for i in range(7)]

    @task(pool="game_api_rate_limit", retries=0, retry_delay=timedelta(minutes=1))
    def flush_stat_by_date(date: str):
        http_hook = HttpHook(method="POST", http_conn_id="game_server")
        response = http_hook.run(
            endpoint="/admin/stats/flush",
            json={"date": date},
        )
        print(response.json())

    dates = get_flush_dates()
    flush_stat_by_date.expand(date=dates)


flush_stat()
