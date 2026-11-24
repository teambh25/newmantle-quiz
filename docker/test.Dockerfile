# Test runner for airflow/ (same Python & Airflow version as airflow.Dockerfile)
# Code is mounted at runtime, so no rebuild is needed when tests or DAGs change.
FROM apache/airflow:2.11.0

# Same runtime libraries as airflow.Dockerfile so DAG modules can be imported
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt pytest

ENV PYTHONDONTWRITEBYTECODE=1
WORKDIR /opt/airflow/project
ENTRYPOINT ["python", "-m", "pytest", "-p", "no:cacheprovider"]
CMD ["tests", "-v"]
