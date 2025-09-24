class BaseException(Exception):
    pass

class DuplicateAnswerException(BaseException):
    pass

class NotFoundInDB(BaseException):
    pass