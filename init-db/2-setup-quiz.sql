-- create quiz db and user
CREATE DATABASE quiz;
CREATE ROLE quiz_admin WITH LOGIN PASSWORD 'quiz';
GRANT ALL PRIVILEGES ON DATABASE quiz TO quiz_admin;

\c quiz;
CREATE EXTENSION IF NOT EXISTS vector;

-- create table
CREATE TABLE IF NOT EXISTS vocabulary (
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    word text UNIQUE NOT NULL,
    emb vector(768) NOT NULL
);

CREATE TABLE IF NOT EXISTS answer (
    "date" Date PRIMARY KEY,
    word_id integer REFERENCES vocabulary (id)
);

-- grant all tables
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO quiz_admin;

-- insert init data
COPY vocabulary(word, emb)
FROM '/embedding/init.csv'
DELIMITER ','
CSV HEADER;
