def raise_for_status(func):
    def wrapper(*args, **kwargs):
        # FIXME: in newer versions of httpx, raise_for_status() is chainable,
        # so we could simply write
        # return func(*args, **kwargs).raise_for_status()
        response = func(*args, **kwargs)
        response.raise_for_status()
        return response

    return wrapper


def raise_for_status_async(func):
    async def wrapper(*args, **kwargs):
        # FIXME: in newer versions of httpx, raise_for_status() is chainable,
        # so we could simply write
        # return func(*args, **kwargs).raise_for_status()
        response = await func(*args, **kwargs)
        response.raise_for_status()
        return response

    return wrapper
