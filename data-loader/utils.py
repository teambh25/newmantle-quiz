import glob
import pickle

def load_embedding(path:str)->dict:
    embeddings = {}
    for p in glob.glob(f"{path}/*"):
        with open(p, 'rb') as f:
            embeddings.update(pickle.load(f))
    return embeddings
