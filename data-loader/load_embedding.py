from utils import load_embedding


def load_embbedding(conn, embeddings: dict):
    cur = conn.cursor()
    with cur.copy('COPY vocabulary (word, embedding) FROM STDIN WITH (FORMAT BINARY)') as copy:
        copy.set_types(['text', 'vector'])
        for i, v in enumerate(embeddings.items()):
            copy.write_row(v)
            while conn.pgconn.flush() == 1:
                pass
    print('\n Setup Vocabulary Table Success!')