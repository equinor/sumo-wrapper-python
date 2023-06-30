import httpx
import logging

from ._auth import Auth
from ._request_error import AuthenticationError, TransientError, PermanentError

logger = logging.getLogger("sumo.wrapper")


def _raise_request_error_exception(code, message):
    """
    Raise the proper authentication error according to the code received from sumo.
    """

    logger.debug("code: %s", code)
    logger.debug("message: %s", message)

    if 503 <= code <= 504 or code == 404 or code == 500:
        raise TransientError(code, message)
    elif 401 <= code <= 403:
        raise AuthenticationError(code, message)
    else:
        raise PermanentError(code, message)


class CallAzureApi:
    """
    This class can be used for generating an Azure OAuth2 bear token and send a request to Azure JSON rest endpoint.
    The Azure clientId "1826bd7c-582f-4838-880d-5b4da5c3eea2" needs to have permissions to the resourceId sent in.

    Parameters
            resourceId:
                Need to be an Azure resourceId
    """

    def __init__(
        self,
        resource_id,
        client_id,
        outside_token=False,
        writeback=False,
        verbosity="CRITICAL",
    ):
        logger.setLevel(level=verbosity)

        self.resource_id = resource_id
        self.client_id = client_id
        self.writeback = writeback
        logger.debug("self.writeback is %s", self.writeback)

        logger.debug("CallAzureApi is initializing")

        logger.debug("resource_id is %s", resource_id)
        logger.debug("client_id is %s", client_id)
        logger.debug("outside_token is %s", outside_token)

        if outside_token:
            self.auth = None
            self.bearer = None
        else:
            logger.debug("outside_token is false, calling self._authenticate")
            self._authenticate()

    def __str__(self):
        str_repr = [
            "{key}='{value}'".format(key=k, value=v)
            for k, v in self.__dict__.items()
        ]
        return ", ".join(str_repr)

    def __repr__(self):
        return self.__str__()

    def get_bearer_token(self):
        """
        Get an Azure OAuth2 bear token.
        You need to open this URL in a web browser https://microsoft.com/devicelogin, and enter the displayed code.

        Return
            accessToken:
                The Bearer Authorization string
        """
        logger.debug("Getting bearer token")
        return self.bearer

    def _authenticate(self):
        """
        Authenticate the user, generating a bearer token that is valid for one hour.
        """
        logger.debug("Running _authenticate")
        self.auth = Auth(self.client_id, self.resource_id, self.writeback)
        self._generate_bearer_token()

    def _generate_bearer_token(self):
        """
        Generate the access token through the authentication object.
        """
        logger.debug("Running _generate_bearer_token()")

        self.bearer = "Bearer " + self.auth.get_token()

        logger.debug(
            "Setting self.bearer. Length of self.bearer is %s",
            str(len(self.bearer)),
        )
        logger.debug("_generate_bearer_token is finished.")

    def _is_token_expired(self):
        """
        Checks if one hour (with five secs tolerance) has passed since last authentication
        """
        logger.debug("Checking if token has expired")

        is_expired = self.auth.is_token_expired()

        logger.debug(
            "Answer from self.auth.is_token_expired() was %s", str(is_expired)
        )

        return is_expired

    def _process_token(self, bearer):
        if bearer:
            logger.debug("Bearer exist, returning bearer")
            return "Bearer " + bearer

        if self._is_token_expired():
            logger.debug("Token is expired, calling for generating it.")
            self._generate_bearer_token()

        logger.debug("self.bearer is being returned from _process_token()")
        logger.debug("Length of self.bearer is %s", str(len(self.bearer)))

        return self.bearer

    def get_json(self, url, bearer=None):
        """
        Send an request to the url.

        Parameters
            url
                Need to be a Azure rest url that returns a JSON.
            bearer
                Optional, if not entered it will generate one by calling the get_bearer_token method

        Return
            json:
                The json respond from the entered URL
        """

        logger.debug("get_json() is starting")

        bearer = self._process_token(bearer)

        headers = {"Content-Type": "application/json", "Authorization": bearer}

        response = httpx.get(url, headers=headers)

        if response.is_error:
            _raise_request_error_exception(response.status_code, response.text)

        return response.json()

    def get_image(self, url, bearer=None):
        """
        Send an request to the url for the image.

        Parameters
            url
                Need to be a Azure rest url that returns a JSON.
            bearer
                Optional, if not entered it will generate one by calling the get_bearer_token method

        Return
            image:
                raw image
        """

        logger.debug("get_image() is starting")

        bearer = self._process_token(bearer)

        headers = {"Content-Type": "html/text", "Authorization": bearer}

        response = httpx.get(url, headers=headers)

        if response.is_error:
            _raise_request_error_exception(response.status_code, response.text)

        return None

    def get_content(self, url, bearer=None):
        """
        Send an request to the url.

        Parameters
            url
                Need to be a Azure rest url that returns a JSON.
            bearer
                Optional, if not entered it will generate one by calling the get_bearer_token method

        Return
           content:
                The content respond from the entered URL.
        """

        logger.debug("get_content() is starting")

        bearer = self._process_token(bearer)

        headers = {"Content-Type": "application/json", "Authorization": bearer}

        response = httpx.get(url, headers=headers)

        if response.is_error:
            _raise_request_error_exception(response.status_code, response.text)

        return response.content

    def post(self, url, blob=None, json=None, bearer=None):
        """
        Post binary or json to the url and return the response as json.

        Parameters
            url: Need to be a Azure rest url that returns a JSON.
            blob: Optional, the binary to save
            json: Optional, the json to save
            bearer: Optional, if not entered it will generate one by calling the get_bearer_token method

        Return
            string: The string respond from the entered URL
        """

        logger.debug("post() is starting")

        bearer = self._process_token(bearer)

        if blob and json:
            raise ValueError(
                "Both blob and json given to post - can only have one at the time."
            )

        headers = {
            "Content-Type": "application/json"
            if json is not None
            else "application/octet-stream",
            "Authorization": bearer,
            "Content-Length": str(len(json) if json else len(blob)),
        }

        try:
            response = httpx.post(url, data=blob, json=json, headers=headers)
        except httpx.ProxyError as err:
            _raise_request_error_exception(503, err)

        if response.is_error:
            _raise_request_error_exception(response.status_code, response.text)

        return response

    def put(self, url, blob=None, json=None, bearer=None):
        """
        Put binary to the url and return the response as json.

        Parameters
            url: Need to be a Azure rest url that returns a JSON.
            blob: Optional, the binary to save
            json: Optional, the json to save
            bearer: Optional, if not entered it will generate one by calling the get_bearer_token method

        Return
            string: The string respond from the entered URL
        """

        logger.debug("put() is starting")

        bearer = self._process_token(bearer)

        if blob and json:
            raise ValueError(
                "Both blob and json given to put - can only have one at the time."
            )

        headers = {
            "Content-Type": "application/json"
            if json is not None
            else "application/octet-stream",
            "Content-Length": str(len(json) if json else len(blob)),
            "x-ms-blob-type": "BlockBlob",
        }

        if url.find("sig=") < 0:
            headers["Authorization"] = bearer

        try:
            response = httpx.put(url, data=blob, json=json, headers=headers)
        except httpx.ProxyError as err:
            _raise_request_error_exception(503, err)

        if response.is_error:
            _raise_request_error_exception(response.status_code, response.text)

        return response

    def delete_object(self, url, bearer=None):
        """
        Send delete to the url and return the response as json.

        Parameters
            url: Need to be a Azure rest url that returns a JSON.
            bearer: Optional, if not entered it will generate one by calling the get_bearer_token method

        Return
            json: The json respond from the entered URL
        """
        logger.debug("delete_object is starting")
        bearer = self._process_token(bearer)

        headers = {
            "Content-Type": "application/json",
            "Authorization": bearer,
        }

        response = httpx.delete(url, headers=headers)

        if response.is_error:
            _raise_request_error_exception(response.status_code, response.text)

        return response.json()
