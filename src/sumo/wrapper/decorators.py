import tenacity as tn

def raise_for_status(func):
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs).raise_for_status()
    return wrapper

def http_unpack(func):
    def wrapper(*args, **kwargs):
        response = func(*args, **kwargs)
        ct = response.headers['Content-Type']
        if ct.startswith('application/octet-stream'):
            return response.content
        if ct.startswith('application/json'):
            return response.json()
        # ELSE:
        return response.text
    return wrapper

# Define the conditions for retrying based on exception types
def is_retryable_exception(exception):
    return isinstance(exception, (httpx.TimeoutException, httpx.ConnectError))

# Define the conditions for retrying based on HTTP status codes
def is_retryable_status_code(response):
    return response.status_code in [502, 503, 504]


def http_retry(func):
    return tn.retry(func,
                    stop=tn.stop_after_attempt(6),
                    retry=(tn.retry_if_exception(is_retryable_exception) |
                           tn.retry_if_result(is_retryable_status_code)),
                    wait=tn.wait_exponential_jitter())
