import httpx

from .decorators import raise_for_status, http_retry


class BlobClient:
    """Upload blobs to blob store using pre-authorized URLs"""

    @raise_for_status
    @http_retry
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

    @raise_for_status
    @http_retry
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
