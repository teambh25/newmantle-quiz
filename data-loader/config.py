import os
from dataclasses import dataclass

@dataclass
class Config:
    DB_USER: str = os.environ['POSTGRES_USER']
    DB_PW: str = os.environ['POSTGRES_PASSWORD']
    DB_NAME: str = os.environ['POSTGRES_DB']
    EMB_DIM: int = int(os.environ['EMB_DIM'])

configs = Config()