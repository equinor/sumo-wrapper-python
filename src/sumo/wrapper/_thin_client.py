import requests
import logging

from .config import APP_REGISTRATION, TENANT_ID, AUTHORITY_HOST_URI
from ._auth import Auth
from ._request_error import AuthenticationError, TransientError, PermanentError

logging.basicConfig(
    format="%(asctime)s %(levelname)-8s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)


class SumoThinClient:
    def __init__(
        self,
        env,
        access_token=None,
        logging_level='INFO',
        write_back=False
    ):
        self.env = env
        self.user_provided_access_token = access_token

        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(level=logging_level)

        if env not in APP_REGISTRATION:
            raise ValueError(f"Invalid environment: {env}")

        self.client_id = APP_REGISTRATION[env]['CLIENT_ID']
        self.resource_id = APP_REGISTRATION[env]['RESOURCE_ID']
        self.authority_uri = AUTHORITY_HOST_URI + '/' + TENANT_ID

        if not self.user_provided_access_token:
            self.auth = Auth(
                client_id=self.client_id,
                resource_id=self.resource_id,
                authority=self.authority_uri,
                writeback=write_back,
                logging_level=logging_level
            )

            self.access_token = self.auth.get_token()

        if env == "localhost":
            self.base_url = f"http://localhost:8084/api/v1"
        else:
            self.base_url = f"https://main-sumo-{env}.radix.equinor.com/api/v1"

    def _retrieve_token(self):
        if self.user_provided_access_token:
            self.logger.debug("User provided token exists, returning token")
            return self.user_provided_access_token
        else:
            if self.auth.is_token_expired():
                self.logger.debug("Token is expired, regenerating")
                self.access_token = self.auth.get_token()

        self.logger.debug("returning self.access_token from _retrieve_token")
        return self.access_token

    def get(self, path, params=None):
        token = self._retrieve_token()

        headers = {
            "Content-Type": "application/json",
            "authorization": f'Bearer {token}'
        }

        response = requests.get(
            f'{self.base_url}{path}',
            params=params,
            headers=headers
        )

        if not response.ok:
            self._raise_request_error_exception(
                response.status_code, response.text)

        if "/blob" in path:
            return response.content

        return response.json()

    def post(self, path, blob=None, json=None):
        token = self._retrieve_token()

        if blob and json:
            raise ValueError(
                "Both blob and json given to post - can only have one at the time.")

        content_type = "application/json" if json is not None else "application/octet-stream"

        headers = {
            "Content-Type": content_type,
            "authorization": f'Bearer {token}',
            "Content-Length": str(len(json) if json else len(blob)),
        }

        try:
            response = requests.post(
                f'{self.base_url}{path}',
                data=blob,
                json=json,
                headers=headers
            )
        except requests.exceptions.ProxyError as err:
            self._raise_request_error_exception(503, err)

        if not response.ok:
            self._raise_request_error_exception(
                response.status_code, response.text)

        return response

    def put(self, path, blob=None, json=None):
        token = self._retrieve_token()

        if blob and json:
            raise ValueError(
                "Both blob and json given to post - can only have one at the time.")

        content_type = "application/json" if json is not None else "application/octet-stream"

        headers = {
            "Content-Type": content_type,
            "authorization": f'Bearer {token}',
            "Content-Length": str(len(json) if json else len(blob)),
        }

        try:
            response = requests.put(
                f'{self.base_url}{path}',
                data=blob,
                json=json,
                headers=headers
            )
        except requests.exceptions.ProxyError as err:
            self. _raise_request_error_exception(503, err)

        if not response.ok:
            self._raise_request_error_exception(
                response.status_code, response.text)

        return response

    def delete(self, path):
        token = self._retrieve_token()

        headers = {
            "Content-Type": "application/json",
            "Authorization": f'Bearer {token}',
        }

        response = requests.delete(f'{self.base_url}{path}', headers=headers)

        if not response.ok:
            self._raise_request_error_exception(
                response.status_code, response.text)

        return response.json()

    def _raise_request_error_exception(self, code, message):
        """
        Raise the proper authentication error according to the code received from sumo.
        """

        self.logger.debug("code: %s", code)
        self.logger.debug("message: %s", message)

        if 503 <= code <= 504 or code == 404 or code == 500:
            raise TransientError(code, message)
        elif 401 <= code <= 403:
            raise AuthenticationError(code, message)
        else:
            raise PermanentError(code, message)
