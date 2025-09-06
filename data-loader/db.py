from loguru import logger


def init_tables(conn, emb_dim: int):
    """
        delete order : answer => vocab
        create order : vocab => answer
    """
    delete_answer_table(conn)
    delete_vocaburary_table(conn)
    create_vocaburary_table(conn, emb_dim)
    create_answer_table(conn)
    logger.success('\n Init Tables Success!')


def create_answer_table(conn):
    conn.execute(
        f"""CREATE TABLE answer (
            date Date PRIMARY KEY,
            word_id integer REFERENCES vocabulary (id)
        )"""
    )    


def create_vocaburary_table(conn, emb_dim: int):
    conn.execute(
        f"""CREATE TABLE vocabulary (
            id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            word text UNIQUE NOT NULL,
            emb vector({emb_dim}) NOT NULL
        )"""
    )


def delete_answer_table(conn):
    conn.execute("DROP TABLE IF EXISTS answer")


def delete_vocaburary_table(conn):
    conn.execute("DROP TABLE IF EXISTS vocabulary")


def insert_embedding(conn, embeddings: dict):
    cur = conn.cursor()
    with cur.copy('COPY vocabulary (word, emb) FROM STDIN WITH (FORMAT BINARY)') as copy:
        copy.set_types(['text', 'vector'])
        for i, v in enumerate(embeddings.items()):
            copy.write_row(v)
            while conn.pgconn.flush() == 1:
                pass
    logger.success('\n Insert Embedding Success!')