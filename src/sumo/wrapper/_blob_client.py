import httpx

from ._decorators import (
    raise_for_status,
    raise_for_status_async,
)

from ._retry_strategy import RetryStrategy


class BlobClient:
    """Upload blobs to blob store using pre-authorized URLs"""

    def __init__(self, retry_strategy=RetryStrategy()):
        self._retry_strategy = retry_strategy
        return

    @raise_for_status
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

        def _put():
            return httpx.put(url, content=blob, headers=headers)

        retryer = self._retry_strategy.make_retryer()

        return retryer(_put)

    @raise_for_status_async
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

        async def _put():
            async with httpx.AsyncClient() as client:
                return await client.put(url=url, content=blob, headers=headers)

        retryer = self._retry_strategy.make_retryer_async()

        return await retryer(_put)
