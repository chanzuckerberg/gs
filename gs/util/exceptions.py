class GSException(Exception):
    """
    Base class for exceptions in this package.
    """

class GetFieldError(GSException):
    pass

class NoServiceCredentials(GSException):
    pass
