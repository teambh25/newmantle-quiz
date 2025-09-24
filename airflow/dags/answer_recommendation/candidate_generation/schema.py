from pydantic import BaseModel

class AnswerCandidate(BaseModel):
    tag: str
    word: str
    description: str