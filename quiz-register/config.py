import os
from dataclasses import dataclass

@dataclass
class Configs:
    server_id: str = os.environ['GAME_SERVER_ID']
    server_pw: str = os.environ['GAME_SERVER_PW']
    server_url: str = os.environ['GAME_SERVER_URL']
    db_user: str = os.environ['POSTGRES_USER']
    db_pw: str = os.environ['POSTGRES_PASSWORD']
    db_name: str = os.environ['POSTGRES_DB']
    emb_dim: int = int(os.environ['EMB_DIM'])

configs = Configs()