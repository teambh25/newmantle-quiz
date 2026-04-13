import os

import requests

_MAX_ERROR_LENGTH = 300
BASE_URL = "http://localhost:5000"


def notify_failure(context):
    webhook_url = os.environ.get("DISCORD_WEBHOOK_URL")
    if not webhook_url:
        print("WARNING: DISCORD_WEBHOOK_URL is not set. Skipping Discord notification.")
        return

    ti = context["task_instance"]
    dag_id = ti.dag_id
    task_id = ti.task_id
    run_id = ti.run_id
    execution_date = context["logical_date"].strftime("%Y-%m-%d %H:%M:%S UTC")

    exception = context.get("exception")
    error_msg = str(exception)[:_MAX_ERROR_LENGTH] if exception else "Unknown error"
    if exception and len(str(exception)) > _MAX_ERROR_LENGTH:
        error_msg += "..."

    ui_link = f"{BASE_URL}/dags/{dag_id}/grid?dag_run_id={run_id}&task_id={task_id}"

    message = (
        f" 🚨 @here **[{dag_id}] Task 실패**\n\n"
        f"• **Task**: `{task_id}`\n"
        f"• **실행 시간**: {execution_date}\n"
        f"• **에러**: {error_msg}\n"
        f"• **Airflow UI**: {ui_link}"
    )

    try:
        response = requests.post(webhook_url, json={"content": message})
        response.raise_for_status()
    except Exception as e:
        print(f"WARNING: Failed to send Discord notification: {e}")
