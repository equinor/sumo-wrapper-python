import asyncio
import contextlib
import logging
import re

import httpx
import jwt

from ._auth_provider import get_auth_provider
from ._blob_client import BlobClient
from ._decorators import (
    raise_for_status,
    raise_for_status_async,
)
from ._logging import LogHandlerSumo
from ._retry_strategy import RetryStrategy
from .config import APP_REGISTRATION, AUTHORITY_HOST_URI, TENANT_ID

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
        case_uuid=None,
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

        self.env = env
        self._verbosity = verbosity

        self._retry_strategy = retry_strategy
        self._client = httpx.Client()
        self._async_client = httpx.AsyncClient()

        self._timeout = timeout

        access_token = None
        refresh_token = None
        if token:
            logger.debug("Token provided")

            payload = None
            with contextlib.suppress(jwt.InvalidTokenError):
                payload = jwt.decode(
                    token, options={"verify_signature": False}
                )

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
            case_uuid=case_uuid,
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

        follow_redirects = False
        if (
            re.match(
                r"^/objects\('[0-9a-fA-F-]{8}-[0-9a-fA-F-]{4}-[0-9a-fA-F-]{4}-[0-9a-fA-F-]{4}-[0-9a-fA-F-]{12}'\)/blob$",  # noqa: E501
                path,
            )
            is not None
        ):
            follow_redirects = True

        def _get():
            return self._client.get(
                f"{self.base_url}{path}",
                params=params,
                headers=headers,
                follow_redirects=follow_redirects,
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

    def create_shared_access_key_for_case(self, case_uuid):
        """Creates and stores a shared access key that can be used to access
        the case identified by *case_uuid*, in the current Sumo environment.

        This shared access key can then be used by instantiating
        SumoClient with the parameter case_uuid set accordingly.

        Args:
            case_uuid: the uuid for a case.

        Side effects:
            Creates a new file in ~/.sumo, named {app_id}+{case_uuid}
        """
        token = self.get(
            f"/objects('{case_uuid}')/make-shared-access-key"
        ).text
        self.auth.store_shared_access_key_for_case(case_uuid, token)

    def client_for_case(self, case_uuid):
        """Instantiate and return new SumoClient for accessing the
        case identified by *case_uuid*."""
        return SumoClient(
            env=self.env,
            verbosity=self._verbosity,
            retry_strategy=self._retry_strategy,
            timeout=self._timeout,
            case_uuid=case_uuid,
        )

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

        follow_redirects = False
        if (
            re.match(
                r"^/objects\('[0-9a-fA-F-]{8}-[0-9a-fA-F-]{4}-[0-9a-fA-F-]{4}-[0-9a-fA-F-]{4}-[0-9a-fA-F-]{12}'\)/blob$",  # noqa: E501
                path,
            )
            is not None
        ):
            follow_redirects = True

        async def _get():
            return await self._async_client.get(
                f"{self.base_url}{path}",
                params=params,
                headers=headers,
                follow_redirects=follow_redirects,
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
