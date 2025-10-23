import pendulum
from datetime import datetime, timedelta

from airflow.decorators import dag, task
from airflow.providers.sftp.hooks.sftp import SFTPHook
  
@dag(
      dag_id="add_missing_words",
      start_date=pendulum.datetime(2025, 9, 19, tz="Asia/Seoul"),
      schedule="0 16 * * 0",  # every sunday at 4pm
      max_active_runs=1,
      catchup=True,
)
def add_missing_words_dag():
    @task
    def fetch_week_logs(data_interval_end: pendulum.datetime):
        hook = SFTPHook(ssh_conn_id="game_server_sftp")
        remote_dir = "/home/ubuntu/newmantle-game/fastapi/logs/game"
        local_dir = "/opt/airflow/data/game-logs"

        end_date = data_interval_end.in_timezone("Asia/Seoul").subtract(days=2)  # The yyyy-mm-dd.log file contains logs for the next day (dd+1)

        date_range = [
            end_date.subtract(days=i).strftime("%Y-%m-%d")
            for i in range(7)
        ]

        print(f"Fetching logs for dates (UTC): {date_range}")

        sftp_client = hook.get_conn()
        all_files = sftp_client.listdir(remote_dir)

        all_downloaded_paths = []
        for log_date in date_range:
            matching_files = [
                f for f in all_files
                if f.startswith(log_date) and f.endswith('.log')
            ]
            if not matching_files:
                print(f"No Math file for {log_date}")

            for filename in matching_files:
                remote_path = f"{remote_dir}/{filename}"
                local_path = f"{local_dir}/{filename}"

                hook.retrieve_file(remote_path, local_path)
                all_downloaded_paths.append(local_path)

            print(f"Downloaded {len(matching_files)} files for {log_date}")

        print(f"Total downloaded: {len(all_downloaded_paths)} files")
        return all_downloaded_paths

    @task
    def process_logs(log_paths: list[str]):
        # 로그 처리 로직
        total_lines = 0
        for log_path in log_paths:
            with open(log_path) as f:
                lines = len(f.readlines())
                total_lines += lines
                print(f"{log_path}: {lines} lines")

        print(f"Total: {total_lines} lines from {len(log_paths)} files")

    log_paths = fetch_week_logs()
    process_logs(log_paths)

add_missing_words_dag()