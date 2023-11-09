import httpx

from ._decorators import (
    is_retryable_exception,
    is_retryable_status_code,
    raise_for_status,
    raise_for_status_async,
    return_last_value,
)
from tenacity import (
    retry,
    retry_if_exception,
    retry_if_result,
    wait_exponential,
    wait_random_exponential,
    stop_after_attempt,
)


class BlobClient:
    """Upload blobs to blob store using pre-authorized URLs"""

    @raise_for_status
    @retry(
        stop=stop_after_attempt(6),
        retry=(
            retry_if_exception(is_retryable_exception)
            | retry_if_result(is_retryable_status_code)
        ),
        wait=wait_exponential(multiplier=0.5)
        + wait_random_exponential(multiplier=0.5),
        reraise=True,
        retry_error_callback=return_last_value,
    )
    def upload_blob(self, blob: bytes, url: str):
        """Upload a blob.

        Parameters:
            blob: byte string to upload
            url: pre-authorized URL to blob store
        """

        headers = {
            "Content-Type": "application/octet-stream",
            "x-ms-blob-type": "BlockBlob",
        }

        response = httpx.put(url, content=blob, headers=headers)

        return response

    @raise_for_status_async
    @retry(
        stop=stop_after_attempt(6),
        retry=(
            retry_if_exception(is_retryable_exception)
            | retry_if_result(is_retryable_status_code)
        ),
        wait=wait_exponential(multiplier=0.5)
        + wait_random_exponential(multiplier=0.5),
        reraise=True,
        retry_error_callback=return_last_value,
    )
    async def upload_blob_async(self, blob: bytes, url: str):
        """Upload a blob async.

        Parameters:
            blob: byte string to upload
            url: pre-authorized URL to blob store
        """

        headers = {
            "Content-Type": "application/octet-stream",
            "x-ms-blob-type": "BlockBlob",
        }

        async with httpx.AsyncClient() as client:
            response = await client.put(url=url, content=blob, headers=headers)

        return response
