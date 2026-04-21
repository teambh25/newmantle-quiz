import pendulum
from airflow.decorators import dag, task
from airflow.providers.sftp.hooks.sftp import SFTPHook


@dag(
    dag_id="fetch_game_event_logs",
    start_date=pendulum.datetime(2026, 4, 5, tz="Asia/Seoul"),
    schedule="0 16 * * 0",  # every sunday at 4pm KST
    max_active_runs=1,
    catchup=True,
)
def fetch_game_event_logs_dag():
    @task
    def fetch_week_logs(data_interval_end: pendulum.DateTime):
        hook = SFTPHook(ssh_conn_id="game_server_sftp")
        remote_dir = "/home/ubuntu/newmantle-game/fastapi/logs/events"
        local_dir = "/opt/airflow/data/game-event-logs"

        # Loguru rotates at UTC 15:00 (KST midnight), naming files by UTC date.
        # Subtract 2 days: YYYY-MM-DD.jsonl.zip covers KST day (DD+1).
        end_date = data_interval_end.in_timezone("Asia/Seoul").subtract(days=2)
        date_range = [end_date.subtract(days=i).strftime("%Y-%m-%d") for i in range(7)]

        print(f"Fetching event logs for dates: {date_range}")

        sftp_client = hook.get_conn()
        all_files = sftp_client.listdir(remote_dir)

        downloaded_paths = []
        for log_date in date_range:
            matching = [
                f for f in all_files if f.startswith(log_date) and f.endswith(".jsonl.zip")
            ]
            if not matching:
                print(f"No event log file for {log_date}")
                continue

            for filename in matching:
                remote_path = f"{remote_dir}/{filename}"
                local_zip_path = f"{local_dir}/{filename}"

                hook.retrieve_file(remote_path, local_zip_path)
                downloaded_paths.append(local_zip_path)
                print(f"Downloaded: {filename}")

        print(f"Total: {len(downloaded_paths)} files fetched")
        return downloaded_paths

    fetch_week_logs()


fetch_game_event_logs_dag()
