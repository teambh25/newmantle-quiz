-- create ariflow db and user
CREATE DATABASE airflow;
CREATE ROLE airflow WITH LOGIN PASSWORD 'airflow';
GRANT ALL PRIVILEGES ON DATABASE airflow TO airflow;

\c airflow
GRANT ALL ON SCHEMA public TO airflow;