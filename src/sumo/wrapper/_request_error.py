class RequestError(Exception):
    def __init__(self, code, message):
        self.code = code
        self.message = message

    def __str__(self):
        return (
            f"Request Error with status code {self.code} "
            f"and text {self.message}"
        )


class AuthenticationError(RequestError):
    def __init__(self, code, message):
        super().__init__(code, message)

    def __str__(self):
        return (
            f"Authentication failed with status code {self.code} "
            f"and text {self.message}."
        )


class TransientError(RequestError):
    def __init__(self, code, message):
        super().__init__(code, message)

    def __str__(self):
        return (
            f"Transient Error with status code {self.code} "
            f"and text {self.message}."
        )


class PermanentError(RequestError):
    def __init__(self, code, message):
        super().__init__(code, message)

    def __str__(self):
        return (
            f"Fatal Request Error with status code {self.code} "
            f"and text {self.message}."
        )


def raise_request_error_exception(code, message):
    """
    Raise the proper authentication error
    according to the code received from sumo.
    """

    if 502 <= code <= 504 or code == 404 or code == 500:
        raise TransientError(code, message)
    elif 401 <= code <= 403:
        raise AuthenticationError(code, message)
    else:
        raise PermanentError(code, message)
