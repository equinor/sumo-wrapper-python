class RequestError(Exception):
    def __init__(self, code, message):
        self.code = code
        self.message = message

    def __str__(self):
        return f'Request Error with status code {self.code} and text {self.message}'


class AuthenticationError(RequestError):
    def __init__(self, code, message):
        super().__init__(code, message)

    def __str__(self):
        return f'Authentication failed with status code {self.code} and text {self.message}.'


class TransientError(RequestError):
    def __init__(self, code, message):
        super().__init__(code, message)

    def __str__(self):
        return f'Transient Error with status code {self.code} and text {self.message}.'


class PermanentError(RequestError):
    def __init__(self, code, message):
        super().__init__(code, message)

    def __str__(self):
        return f'Fatal Request Error with status code {self.code} and text {self.message}.'
