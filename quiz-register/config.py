import os
from dataclasses import dataclass

@dataclass
class Config:
    ADMIN_ID: str = os.environ['ADMIN_ID']
    ADMIN_PW: str = os.environ['ADMIN_PW']
    GAME_SERVER_URL: str = os.environ['GAME_SERVER_URL']

configs = Config()