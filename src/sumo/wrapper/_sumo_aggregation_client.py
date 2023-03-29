import logging
import time

import jwt
import requests

from ._new_auth import NewAuth
from ._request_error import raise_request_error_exception
from .config import AGG_APP_REGISTRATION, TENANT_ID

logger = logging.getLogger("sumo.wrapper")


class SumoAggregationClient:
    def __init__(
        self,
        env: str,
        token: str = None,
        interactive: bool = False,
        verbosity: str = "CRITICAL",
    ):
        """Initialize a new Sumo Aggregation object
        Args:
            env: Sumo environment
            token: Access token or refresh token.
            interactive: Enable interactive authentication (in browser).
                If not enabled, code grant flow will be used.
            verbosity: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        """

        logger.setLevel(verbosity)

        if env not in AGG_APP_REGISTRATION:
            raise ValueError(f"Invalid environment: {env}")

        self.access_token = None
        self.access_token_expires = None
        if token:
            logger.debug("Token provided")
            payload = self.__decode_token(token)

            if payload:
                logger.debug(f"Token decoded as JWT, payload: {payload}")
                self.access_token = token
                self.access_token_expires = payload["exp"]
            else:
                logger.debug("Unable to decode token as JWT")
        else:
            self.auth = NewAuth(
                client_id=AGG_APP_REGISTRATION[env]["CLIENT_ID"],
                resource_id=AGG_APP_REGISTRATION[env]["RESOURCE_ID"],
                tenant_id=TENANT_ID,
                interactive=interactive,
                verbosity=verbosity,
            )

        if env == "localhost":
            self.base_url = (
                "https://main-sumo-surface-aggregation-service-preview"
                + ".radix.equinor.com"
            )
        else:
            self.base_url = (
                f"https://main-sumo-surface-aggregation-service-{env}"
                + ".radix.equinor.com"
            )

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

    def get_aggregate(self, json: dict):
        """
        Performs a POST-request to Sumo Aggregation API /fastaggregation.

        Takes json with objects to aggregate and aggregation operation
            as payload
        Args:
            json: Json payload
        Returns:
            Sumo aggregate response object
        """
        token = self._retrieve_token()

        headers = {
            "Content-Type": "application/json",
            "authorization": f"Bearer {token}",
            "Content-Length": str(len(json)),
        }

        try:
            response = requests.post(
                f"{self.base_url}/fastaggregation", json=json, headers=headers
            )
        except requests.exceptions.ProxyError as err:
            raise_request_error_exception(503, err)

        if not response.ok:
            raise_request_error_exception(response.status_code, response.text)

        return response
