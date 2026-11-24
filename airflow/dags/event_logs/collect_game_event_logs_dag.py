import gzip
import os
import re
import shlex
import shutil
from datetime import date, timedelta

import pendulum
from airflow.decorators import dag, task
from airflow.providers.ssh.hooks.ssh import SSHHook

REMOTE_DIR = "/home/ubuntu/newmantle-game/fastapi/logs/raw-events"
LOCAL_DIR = "/opt/airflow/data/game-logs/raw-events"

# {UTC date}.{pid}.jsonl — loguru rotates file D at D+1 15:00Z.
# On a same-name rotation loguru renames to {date}.{pid}.{timestamp}.jsonl.
REMOTE_FILE_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})\..+\.jsonl$")


def select_files(remote_names, local_names, run_date: date) -> list[str]:
    """Finished (date <= run_date - 2) and not yet fetched remote files."""
    cutoff = run_date - timedelta(days=2)
    fetched = set(local_names)
    selected = []
    for name in remote_names:
        m = REMOTE_FILE_RE.match(name)
        if not m or date.fromisoformat(m.group(1)) > cutoff:
            continue
        if f"{name}.gz" in fetched:
            continue
        selected.append(name)
    return sorted(selected)


def verify_gzip(path: str) -> int:
    """Read the whole gzip stream; return line count (raises if corrupt)."""
    with gzip.open(path, "rb") as f:
        return sum(1 for _ in f)


def fetch_gzipped(ssh, remote_path: str, local_path: str) -> int:
    tmp_path = f"{local_path}.tmp"
    try:
        _, stdout, stderr = ssh.exec_command(f"gzip -c {shlex.quote(remote_path)}")
        with open(tmp_path, "wb") as f:
            shutil.copyfileobj(stdout, f)
        status = stdout.channel.recv_exit_status()
        if status != 0:
            raise RuntimeError(f"gzip exit {status}: {stderr.read().decode()}")
        lines = verify_gzip(tmp_path)
        os.replace(tmp_path, local_path)
        return lines
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


@dag(
    dag_id="collect_game_event_logs",
    start_date=pendulum.datetime(2026, 11, 23, tz="Asia/Seoul"),
    schedule="0 16 * * *",  # daily 4pm KST
    max_active_runs=1,
    catchup=False,
)
def collect_game_event_logs_dag():
    @task
    def collect(data_interval_end: pendulum.DateTime):
        run_date = data_interval_end.in_timezone("UTC").date()
        ssh = SSHHook(ssh_conn_id="game_server_sftp").get_conn()
        try:
            remote_names = ssh.open_sftp().listdir(REMOTE_DIR)
            targets = select_files(remote_names, os.listdir(LOCAL_DIR), run_date)
            print(f"run_date(UTC)={run_date}, targets={targets}")

            failed = []
            for name in targets:
                try:
                    lines = fetch_gzipped(
                        ssh, f"{REMOTE_DIR}/{name}", f"{LOCAL_DIR}/{name}.gz"
                    )
                    print(f"Fetched {name}: {lines} lines")
                except Exception as e:
                    print(f"Failed {name}: {e!r}")
                    failed.append(name)
        finally:
            ssh.close()

        if failed:
            raise RuntimeError(f"{len(failed)}/{len(targets)} failed: {failed}")

    collect()


collect_game_event_logs_dag()
