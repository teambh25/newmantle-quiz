from loguru import logger


def create_vocaburary_table(conn, emb_dim):
    conn.execute("DROP TABLE IF EXISTS vocabulary")
    conn.execute(
        f"""CREATE TABLE vocabulary (
            id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            word text UNIQUE NOT NULL,
            embedding vector({emb_dim}) NOT NULL
        )"""
    )
    logger.success('\n Setup Vocabulary Table Success!')


def create_answer_table(conn):
    conn.execute("DROP TABLE IF EXISTS answer")
    conn.execute(
        f"""CREATE TABLE answer (
            date Date PRIMARY KEY,
            word_id integer REFERENCES vocabulary (id)
        )"""
    )
    logger.success('\n Setup Answer Table Success!')


def insert_embedding(conn, embeddings: dict):
    cur = conn.cursor()
    with cur.copy('COPY vocabulary (word, embedding) FROM STDIN WITH (FORMAT BINARY)') as copy:
        copy.set_types(['text', 'vector'])
        for i, v in enumerate(embeddings.items()):
            copy.write_row(v)
            while conn.pgconn.flush() == 1:
                pass
    logger.success('\n Insert Embedding Success!')