import logging
import time

import httpx
import jwt

from ._blob_client import BlobClient
from ._logging import LogHandlerSumo
from ._new_auth import NewAuth
from ._request_error import raise_request_error_exception
from .config import APP_REGISTRATION, TENANT_ID

logger = logging.getLogger("sumo.wrapper")


class SumoClient:
    """Authenticate and perform requests to the Sumo API."""

    def __init__(
        self,
        env: str,
        token: str = None,
        interactive: bool = False,
        verbosity: str = "CRITICAL",
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

        self.access_token = None
        self.access_token_expires = None
        self.refresh_token = None
        self._blob_client = BlobClient()

        if token:
            logger.debug("Token provided")
            payload = self.__decode_token(token)

            if payload:
                logger.debug(f"Token decoded as JWT, payload: {payload}")
                self.access_token = token
                self.access_token_expires = payload["exp"]
            else:
                logger.debug(
                    "Unable to decode token as JWT, "
                    "treating it as a refresh token"
                )
                self.refresh_token = token
        else:
            self.auth = NewAuth(
                client_id=APP_REGISTRATION[env]["CLIENT_ID"],
                resource_id=APP_REGISTRATION[env]["RESOURCE_ID"],
                tenant_id=TENANT_ID,
                interactive=interactive,
                refresh_token=self.refresh_token,
                verbosity=verbosity,
            )

        if env == "localhost":
            self.base_url = "http://localhost:8084/api/v1"
        else:
            self.base_url = f"https://main-sumo-{env}.radix.equinor.com/api/v1"

    def authenticate(self) -> str:
        """Authenticate to Sumo.

        If no access token/refresh token has been provided,
        this will result in an authentication prompt.

        Returns:
            An access token
        """

        return self._retrieve_token()

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

        return self._blob_client

    def __decode_token(self, token: str) -> dict:
        """
        Decodes a Json Web Token, returns the payload as a dictionary.

        Args:
            token: Token to decode

        Returns:
            Decoded Json Web Token (None if token can't be decoded)
        """

        try:
            payload = jwt.decode(token, options={"verify_signature": False})
            return payload
        except jwt.InvalidTokenError:
            return None

    def _retrieve_token(self) -> str:
        """Retrieve a token for the Sumo API.

        Returns:
            A Json Web Token
        """

        if self.access_token:
            logger.debug(
                "User provided access_token exists, " "checking expire time"
            )
            if self.access_token_expires <= int(time.time()):
                raise ValueError("Access_token has expired")
            else:
                logger.debug("Returning user provided access token")
                return self.access_token

        logger.debug("No user provided token exists, retrieving access token")
        return self.auth.get_token()

    def _process_params(self, params_dict: dict) -> dict:
        """Convert a dictionary of query parameters to Sumo friendly format.

        Args:
            params_dict: Dictionary of query parameters

        Returns:
            Dictionary of processed parameters
        """

        prefixed_params = {}

        for param_key in params_dict:
            prefixed_params[f"${param_key}"] = params_dict[param_key]

        return None if prefixed_params == {} else prefixed_params

    def get(self, path: str, **params) -> dict:
        """Performs a GET-request to the Sumo API.

        Args:
            path: Path to a Sumo endpoint
            params: Keyword arguments treated as query parameters

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

        token = self._retrieve_token()

        headers = {
            "Content-Type": "application/json",
            "authorization": f"Bearer {token}",
        }

        response = httpx.get(
            f"{self.base_url}{path}",
            params=self._process_params(params),
            headers=headers,
            follow_redirects=True,
        )

        if response.is_error:
            raise_request_error_exception(response.status_code, response.text)

        if "/blob" in path:
            return response.content

        return response.json()

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

                new_objet = sumo.post(
                    path=f"/objects('{new_case_id}')",
                    json=object_metadata
                )
        """

        token = self._retrieve_token()

        if blob and json:
            raise ValueError("Both blob and json given to post.")

        content_type = (
            "application/octet-stream" if blob else "application/json"
        )
        content_length = 0

        if blob or json:
            content_length = len(str(json)) if json else len(blob)

        headers = {
            "Content-Type": content_type,
            "authorization": f"Bearer {token}",
            "Content-Length": str(content_length),
        }

        try:
            response = httpx.post(
                f"{self.base_url}{path}",
                data=blob,
                json=json,
                headers=headers,
                params=params,
            )
        except httpx.ProxyError as err:
            raise_request_error_exception(503, err)

        if response.is_error:
            raise_request_error_exception(response.status_code, response.text)

        return response

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

        token = self._retrieve_token()

        if blob and json:
            raise ValueError("Both blob and json given to post")

        content_type = (
            "application/json"
            if json is not None
            else "application/octet-stream"
        )

        headers = {
            "Content-Type": content_type,
            "authorization": f"Bearer {token}",
            "Content-Length": str(len(str(json)) if json else len(blob)),
        }

        try:
            response = httpx.put(
                f"{self.base_url}{path}", data=blob, json=json, headers=headers
            )
        except httpx.ProxyError as err:
            raise_request_error_exception(503, err)

        if response.is_error:
            raise_request_error_exception(response.status_code, response.text)

        return response

    def delete(self, path: str) -> dict:
        """Performs a DELETE-request to the Sumo API.

        Args:
            path: Path to a Sumo endpoint

        Returns:
            Sumo JSON resposne as a dictionary

        Examples:
            Deleting object::

                object_id = ...
                sumo = SumoClient("dev")

                sumo.delete(path=f"/objects('{object_id}')")
        """

        token = self._retrieve_token()

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        }

        response = httpx.delete(f"{self.base_url}{path}", headers=headers)

        if response.is_error:
            raise_request_error_exception(response.status_code, response.text)

        return response.json()

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
        handler = LogHandlerSumo(self)
        logger.addHandler(handler)
        return logger

    async def get_async(self, path: str, **params):
        """Performs an async GET-request to the Sumo API.

        Args:
            path: Path to a Sumo endpoint
            params: Keyword arguments treated as query parameters

        Returns:
            Sumo JSON response as a dictionary

        Examples:
            Retrieving user data from Sumo::

                sumo = SumoClient("dev")

                userdata = await sumo.getAsync(path="/userdata")

            Searching for cases::

                sumo = SuomClient("dev")

                cases = await sumo.getAsync(
                    path="/search",
                    query="class:case",
                    size=3
                )
        """
        token = self._retrieve_token()

        headers = {
            "Content-Type": "application/json",
            "authorization": f"Bearer {token}",
        }

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}{path}",
                params=self._process_params(params),
                headers=headers,
            )

        if response.is_error:
            raise_request_error_exception(response.status_code, response.text)

        if "/blob" in path:
            return response.content

        return response.json()

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

        Returns:
            Sumo response object

        Raises:
            ValueError: If both blob and json parameters have been provided

        Examples:
            Uploading case metadata::

                case_metadata = {...}
                sumo = SumoClient("dev")

                new_case = await sumo.postAsync(
                    path="/objects",
                    json=case_metadata
                )

                new_case_id = new_case.json()["_id"]

            Uploading object metadata::

                object_metadata = {...}
                sumo = SumoClient("dev")

                new_objet = await sumo.postAsync(
                    path=f"/objects('{new_case_id}')",
                    json=object_metadata
                )
        """

        token = self._retrieve_token()

        if blob and json:
            raise ValueError("Both blob and json given to post.")

        content_type = (
            "application/octet-stream" if blob else "application/json"
        )
        content_length = 0

        if blob or json:
            content_length = len(str(json)) if json else len(blob)

        headers = {
            "Content-Type": content_type,
            "authorization": f"Bearer {token}",
            "Content-Length": str(content_length),
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url=f"{self.base_url}{path}",
                    data=blob,
                    json=json,
                    headers=headers,
                    params=params,
                )
        except httpx.ProxyError as err:
            raise_request_error_exception(503, err)

        if response.is_error:
            raise_request_error_exception(response.status_code, response.text)

        return response

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

        token = self._retrieve_token()

        if blob and json:
            raise ValueError("Both blob and json given to post")

        content_type = (
            "application/json"
            if json is not None
            else "application/octet-stream"
        )

        headers = {
            "Content-Type": content_type,
            "authorization": f"Bearer {token}",
            "Content-Length": str(len(str(json)) if json else len(blob)),
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.put(
                    url=f"{self.base_url}{path}",
                    data=blob,
                    json=json,
                    headers=headers,
                )
        except httpx.ProxyError as err:
            raise_request_error_exception(503, err)

        if response.is_error:
            raise_request_error_exception(response.status_code, response.text)

        return response

    async def delete_async(self, path: str) -> dict:
        """Performs an async DELETE-request to the Sumo API.

        Args:
            path: Path to a Sumo endpoint

        Returns:
            Sumo JSON resposne as a dictionary

        Examples:
            Deleting object::

                object_id = ...
                sumo = SumoClient("dev")

                await sumo.deleteAsync(path=f"/objects('{object_id}')")
        """

        token = self._retrieve_token()

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        }

        async with httpx.AsyncClient() as client:
            response = await client.delete(
                url=f"{self.base_url}{path}",
                headers=headers,
            )

        if response.is_error:
            raise_request_error_exception(response.status_code, response.text)

        return response.json()
