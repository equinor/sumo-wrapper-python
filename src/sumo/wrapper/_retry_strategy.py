import tenacity as tn
import httpx


def _log_retry_info(retry_state):
    # logger.log(
    #     logging.INFO,
    #     f"Attempts: {retry_state.attempt_number}; "
    #     f"Elapsed: {retry_state.seconds_since_start}",
    # )
    print(
        f"Attempts: {retry_state.attempt_number}; "
        f"Elapsed:  {retry_state.seconds_since_start}"
    )
    return


# Define the conditions for retrying based on exception types
def _is_retryable_exception(exception):
    return isinstance(exception, (httpx.TimeoutException, httpx.ConnectError))


# Define the conditions for retrying based on HTTP status codes
def _is_retryable_status_code(response):
    return response.status_code in [502, 503, 504]


def _return_last_value(retry_state):
    return retry_state.outcome.result()


class RetryStrategy:
    def __init__(self, stop_after=6, multiplier=0.5, exp_base=2):
        self._stop_after = stop_after
        self._multiplier = multiplier
        self._exp_base = exp_base
        return

    def make_retryer(self):
        return tn.Retrying(
            stop=tn.stop_after_attempt(self._stop_after),
            retry=(
                tn.retry_if_exception(_is_retryable_exception)
                | tn.retry_if_result(_is_retryable_status_code)
            ),
            wait=(
                tn.wait_exponential(
                    multiplier=self._multiplier, exp_base=self._exp_base
                )
                + tn.wait_random_exponential(
                    multiplier=self._multiplier, exp_base=self._exp_base
                )
            ),
            retry_error_callback=_return_last_value,
            before_sleep=_log_retry_info,
        )

    def make_retryer_async(self):
        return tn.AsyncRetrying(
            stop=tn.stop_after_attempt(self._stop_after),
            retry=(
                tn.retry_if_exception(_is_retryable_exception)
                | tn.retry_if_result(_is_retryable_status_code)
            ),
            wait=(
                tn.wait_exponential(
                    multiplier=self._multiplier, exp_base=self._exp_base
                )
                + tn.wait_random_exponential(
                    multiplier=self._multiplier, exp_base=self._exp_base
                )
            ),
            retry_error_callback=_return_last_value,
            before_sleep=_log_retry_info,
        )
