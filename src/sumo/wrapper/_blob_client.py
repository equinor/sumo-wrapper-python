from ._decorators import (
    raise_for_status,
    raise_for_status_async,
)


class BlobClient:
    """Upload blobs to blob store using pre-authorized URLs"""

    def __init__(self, client, async_client, timeout, retry_strategy):
        self._client = client
        self._async_client = async_client
        self._timeout = timeout
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
            return self._client.put(
                url, content=blob, headers=headers, timeout=self._timeout
            )

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
            return await self._async_client.put(
                url=url, content=blob, headers=headers, timeout=self._timeout
            )

        retryer = self._retry_strategy.make_retryer_async()

        return await retryer(_put)
