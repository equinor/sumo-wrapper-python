# For sphinx:
from functools import wraps

from sumo.wrapper._auth_provider import AuthProviderSumoToken


def raise_for_status(func):
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        # FIXME: in newer versions of httpx, raise_for_status() is chainable,
        # so we could simply write
        # return func(*args, **kwargs).raise_for_status()
        response = func(self, *args, **kwargs)
        if response.status_code == 401 and isinstance(
            self.auth, AuthProviderSumoToken
        ):
            self._handle_invalid_shared_key()
        response.raise_for_status()
        return response

    return wrapper


def raise_for_status_async(func):
    @wraps(func)
    async def wrapper(self, *args, **kwargs):
        # FIXME: in newer versions of httpx, raise_for_status() is chainable,
        # so we could simply write
        # return func(*args, **kwargs).raise_for_status()
        response = await func(self, *args, **kwargs)
        if response.status_code == 401 and isinstance(
            self.auth, AuthProviderSumoToken
        ):
            self._handle_invalid_shared_key()
        response.raise_for_status()
        return response

    return wrapper
