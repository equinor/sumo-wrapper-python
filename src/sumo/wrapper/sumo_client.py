import logging
import asyncio
import httpx
import jwt

from ._blob_client import BlobClient
from ._logging import LogHandlerSumo
from ._auth_provider import get_auth_provider
from .config import APP_REGISTRATION, TENANT_ID, AUTHORITY_HOST_URI

from ._decorators import (
    raise_for_status,
    raise_for_status_async,
)

from ._retry_strategy import RetryStrategy

logger = logging.getLogger("sumo.wrapper")

DEFAULT_TIMEOUT = httpx.Timeout(30.0)


class SumoClient:
    """Authenticate and perform requests to the Sumo API."""

    def __init__(
        self,
        env: str,
        token: str = None,
        interactive: bool = False,
        devicecode: bool = False,
        verbosity: str = "CRITICAL",
        retry_strategy=RetryStrategy(),
        timeout=DEFAULT_TIMEOUT,
    ):
        """Initialize a new Sumo object

        Args:
            env: Sumo environment
            token: Access token or refresh token.
            interactive: Enable interactive authentication (in browser).
                If not enabled, code grant flow will be used.
            verbosity: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        """

        logger.setLevel(verbosity)

        if env not in APP_REGISTRATION:
            raise ValueError(f"Invalid environment: {env}")

        self._retry_strategy = retry_strategy
        self._client = httpx.Client(follow_redirects=True)
        self._async_client = httpx.AsyncClient(follow_redirects=True)

        self._timeout = timeout

        access_token = None
        refresh_token = None
        if token:
            logger.debug("Token provided")

            payload = None
            try:
                payload = jwt.decode(
                    token, options={"verify_signature": False}
                )
            except jwt.InvalidTokenError:
                pass

            if payload:
                logger.debug(f"Token decoded as JWT, payload: {payload}")
                access_token = token
            else:
                logger.debug(
                    "Unable to decode token as JWT, "
                    "treating it as a refresh token"
                )
                refresh_token = token
                pass
            pass
        self.auth = get_auth_provider(
            client_id=APP_REGISTRATION[env]["CLIENT_ID"],
            authority=f"{AUTHORITY_HOST_URI}/{TENANT_ID}",
            resource_id=APP_REGISTRATION[env]["RESOURCE_ID"],
            interactive=interactive,
            refresh_token=refresh_token,
            access_token=access_token,
            devicecode=devicecode,
        )

        if env == "localhost":
            self.base_url = "http://localhost:8084/api/v1"
        else:
            self.base_url = f"https://main-sumo-{env}.radix.equinor.com/api/v1"
            pass
        return

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self._client.close()
        self._client = None
        return False

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        await self._async_client.aclose()
        self._async_client = None
        return False

    def __del__(self):
        if self._client is not None:
            self._client.close()
            self._client = None
            pass
        if self._async_client is not None:

            async def closeit(client):
                await client.aclose()
                return

            try:
                loop = asyncio.get_running_loop()
                loop.create_task(closeit(self._async_client))
            except RuntimeError:
                pass
            self._async_client = None
            pass

    def authenticate(self):
        if self.auth is None:
            return None
        return self.auth.get_token()

    @property
    def blob_client(self) -> BlobClient:
        """Get blob_client

        Used for uploading blob using a pre-authorized blob URL.

        Examples:
            Uploading blob::

                blob = ...
                blob_url = ...
                sumo = SumoClient("dev")

                sumo.blob_client.upload_blob(blob, blob_url)

            Uploading blob async::

                await sumo.blob_client.upload_blob_async(blob, blob_url)
        """

        return BlobClient(
            self._client,
            self._async_client,
            self._timeout,
            self._retry_strategy,
        )

    @raise_for_status
    def get(self, path: str, params: dict = None) -> dict:
        """Performs a GET-request to the Sumo API.

        Args:
            path: Path to a Sumo endpoint
            params: query parameters, as dictionary

        Returns:
            Sumo JSON response as a dictionary

        Examples:
            Retrieving user data from Sumo::

                sumo = SumoClient("dev")

                userdata = sumo.get(path="/userdata")

            Searching for cases::

                sumo = SuomClient("dev")

                cases = sumo.get(
                    path="/search",
                    query="class:case",
                    size=3
                )
        """

        headers = {
            "Content-Type": "application/json",
        }

        headers.update(self.auth.get_authorization())

        def _get():
            return self._client.get(
                f"{self.base_url}{path}",
                params=params,
                headers=headers,
                follow_redirects=True,
                timeout=self._timeout,
            )

        retryer = self._retry_strategy.make_retryer()

        return retryer(_get)

    @raise_for_status
    def post(
        self,
        path: str,
        blob: bytes = None,
        json: dict = None,
        params: dict = None,
    ) -> httpx.Response:
        """Performs a POST-request to the Sumo API.

        Takes either blob or json as a payload,
        will raise an error if both are provided.

        Args:
            path: Path to a Sumo endpoint
            blob: Blob payload
            json: Json payload
            params: query parameters, as dictionary

        Returns:
            Sumo response object

        Raises:
            ValueError: If both blob and json parameters have been provided

        Examples:
            Uploading case metadata::

                case_metadata = {...}
                sumo = SumoClient("dev")

                new_case = sumo.post(
                    path="/objects",
                    json=case_metadata
                )

                new_case_id = new_case.json()["_id"]

            Uploading object metadata::

                object_metadata = {...}
                sumo = SumoClient("dev")

                new_object = sumo.post(
                    path=f"/objects('{new_case_id}')",
                    json=object_metadata
                )
        """
        if blob and json:
            raise ValueError("Both blob and json given to post.")

        content_type = (
            "application/octet-stream" if blob else "application/json"
        )

        headers = {
            "Content-Type": content_type,
        }

        headers.update(self.auth.get_authorization())

        def _post():
            return self._client.post(
                f"{self.base_url}{path}",
                content=blob,
                json=json,
                headers=headers,
                params=params,
                timeout=self._timeout,
            )

        retryer = self._retry_strategy.make_retryer()

        return retryer(_post)

    @raise_for_status
    def put(
        self, path: str, blob: bytes = None, json: dict = None
    ) -> httpx.Response:
        """Performs a PUT-request to the Sumo API.

        Takes either blob or json as a payload,
        will raise an error if both are provided.

        Args:
            path: Path to a Sumo endpoint
            blob: Blob payload
            json: Json payload

        Returns:
            Sumo response object
        """

        if blob and json:
            raise ValueError("Both blob and json given to post")

        content_type = (
            "application/json"
            if json is not None
            else "application/octet-stream"
        )

        headers = {
            "Content-Type": content_type,
        }

        headers.update(self.auth.get_authorization())

        def _put():
            return self._client.put(
                f"{self.base_url}{path}",
                content=blob,
                json=json,
                headers=headers,
                timeout=self._timeout,
            )

        retryer = self._retry_strategy.make_retryer()

        return retryer(_put)

    @raise_for_status
    def delete(self, path: str, params: dict = None) -> dict:
        """Performs a DELETE-request to the Sumo API.

        Args:
            path: Path to a Sumo endpoint
            params: query parameters, as dictionary

        Returns:
            Sumo JSON resposne as a dictionary

        Examples:
            Deleting object::

                object_id = ...
                sumo = SumoClient("dev")

                sumo.delete(path=f"/objects('{object_id}')")
        """

        headers = {
            "Content-Type": "application/json",
        }

        headers.update(self.auth.get_authorization())

        def _delete():
            return self._client.delete(
                f"{self.base_url}{path}",
                headers=headers,
                params=params,
                timeout=self._timeout,
            )

        retryer = self._retry_strategy.make_retryer()

        return retryer(_delete)

    def getLogger(self, name):
        """Gets a logger object that sends log objects into the message_log
        index for the Sumo instance.

        Args:
            name: string naming the logger instance

        Returns:
            logger instance

        See Python documentation for logging.Logger for details.
        """

        logger = logging.getLogger(name)
        if len(logger.handlers) == 0:
            handler = LogHandlerSumo(self)
            logger.addHandler(handler)
            pass
        return logger

    @raise_for_status_async
    async def get_async(self, path: str, params: dict = None):
        """Performs an async GET-request to the Sumo API.

        Args:
            path: Path to a Sumo endpoint
            params: query parameters, as dictionary

        Returns:
            Sumo JSON response as a dictionary

        Examples:
            Retrieving user data from Sumo::

                sumo = SumoClient("dev")

                userdata = await sumo.get_async(path="/userdata")

            Searching for cases::

                sumo = SuomClient("dev")

                cases = await sumo.get_async(
                    path="/search",
                    query="class:case",
                    size=3
                )
        """

        headers = {
            "Content-Type": "application/json",
        }

        headers.update(self.auth.get_authorization())

        async def _get():
            return await self._async_client.get(
                f"{self.base_url}{path}",
                params=params,
                headers=headers,
                timeout=self._timeout,
            )

        retryer = self._retry_strategy.make_retryer_async()

        return await retryer(_get)

    @raise_for_status_async
    async def post_async(
        self,
        path: str,
        blob: bytes = None,
        json: dict = None,
        params: dict = None,
    ) -> httpx.Response:
        """Performs an async POST-request to the Sumo API.

        Takes either blob or json as a payload,
        will raise an error if both are provided.

        Args:
            path: Path to a Sumo endpoint
            blob: Blob payload
            json: Json payload
            params: query parameters, as dictionary

        Returns:
            Sumo response object

        Raises:
            ValueError: If both blob and json parameters have been provided

        Examples:
            Uploading case metadata::

                case_metadata = {...}
                sumo = SumoClient("dev")

                new_case = await sumo.post_async(
                    path="/objects",
                    json=case_metadata
                )

                new_case_id = new_case.json()["_id"]

            Uploading object metadata::

                object_metadata = {...}
                sumo = SumoClient("dev")

                new_object = await sumo.post_async(
                    path=f"/objects('{new_case_id}')",
                    json=object_metadata
                )
        """

        if blob and json:
            raise ValueError("Both blob and json given to post.")

        content_type = (
            "application/octet-stream" if blob else "application/json"
        )

        headers = {
            "Content-Type": content_type,
        }

        headers.update(self.auth.get_authorization())

        async def _post():
            return await self._async_client.post(
                url=f"{self.base_url}{path}",
                content=blob,
                json=json,
                headers=headers,
                params=params,
                timeout=self._timeout,
            )

        retryer = self._retry_strategy.make_retryer_async()

        return await retryer(_post)

    @raise_for_status_async
    async def put_async(
        self, path: str, blob: bytes = None, json: dict = None
    ) -> httpx.Response:
        """Performs an async PUT-request to the Sumo API.

        Takes either blob or json as a payload,
        will raise an error if both are provided.

        Args:
            path: Path to a Sumo endpoint
            blob: Blob payload
            json: Json payload

        Returns:
            Sumo response object
        """

        if blob and json:
            raise ValueError("Both blob and json given to post")

        content_type = (
            "application/json"
            if json is not None
            else "application/octet-stream"
        )

        headers = {
            "Content-Type": content_type,
        }

        headers.update(self.auth.get_authorization())

        async def _put():
            return await self._async_client.put(
                url=f"{self.base_url}{path}",
                content=blob,
                json=json,
                headers=headers,
                timeout=self._timeout,
            )

        retryer = self._retry_strategy.make_retryer_async()

        return await retryer(_put)

    @raise_for_status_async
    async def delete_async(self, path: str, params: dict = None) -> dict:
        """Performs an async DELETE-request to the Sumo API.

        Args:
            path: Path to a Sumo endpoint
            params: query parameters, as dictionary

        Returns:
            Sumo JSON resposne as a dictionary

        Examples:
            Deleting object::

                object_id = ...
                sumo = SumoClient("dev")

                await sumo.delete_async(path=f"/objects('{object_id}')")
        """

        headers = {
            "Content-Type": "application/json",
        }

        headers.update(self.auth.get_authorization())

        async def _delete():
            return await self._async_client.delete(
                url=f"{self.base_url}{path}",
                headers=headers,
                params=params,
                timeout=self._timeout,
            )

        retryer = self._retry_strategy.make_retryer_async()

        return await retryer(_delete)
