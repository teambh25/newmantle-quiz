FROM apache/airflow:2.11.0
RUN pip install --no-cache-dir \
    apache-airflow-providers-postgres \
    apache-airflow-providers-http \ 
    google-genai