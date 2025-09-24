class BaseException(Exception):
    def __init__(self, msg):
        self.msg = msg
        super().__init__(msg)

class DuplicateAnswerException(BaseException):
    pass

class NotFoundInDB(BaseException):
    pass