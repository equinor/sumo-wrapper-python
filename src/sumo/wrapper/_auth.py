import datetime
import msal
import json
import stat
import sys
import os

TENANT = "3aa4a235-b6e2-48d5-9195-7fcf05b459b0"

AUTHORITY_HOST_URI = "https://login.microsoftonline.com"
AUTHORITY_URI = AUTHORITY_HOST_URI + "/" + TENANT
HOME_DIR = os.path.expanduser("~")


class Auth:
    def __init__(
        self, client_id, resource_id, authority=AUTHORITY_URI, client_credentials=None
    ):
        self.client_id = client_id
        self.resource_id = resource_id
        self.scope = self.resource_id + "/.default"
        self.authority = authority
        self.client_credentials = client_credentials
        self.token_path = os.path.join(
            HOME_DIR, ".sumo", str(self.resource_id) + ".token"
        )
        self._get_cache()
        self.app = msal.PublicClientApplication(
            self.client_id,
            authority=AUTHORITY_URI,
            client_credential=self.client_credentials,
            token_cache=self.cache,
        )
        self.accounts = self.app.get_accounts()

        if self._cache_available():
            if not self.accounts:
                print("Token cache found but have no accounts")
                self._oauth_device_code()
            else:
                self._oauth_get_token_silent()
        else:
            print("No token cache found, reauthenticate")
            self._oauth_device_code()

    def get_token(self):
        if self.is_token_expired():
            self._oauth_get_token_silent()

        return self.result["access_token"]

    def is_token_expired(self):
        """
        Check if token is expired or about to expire.
        """
        return datetime.datetime.now() > self.expiring_date

    def _oauth_get_token_silent(self):
        if not self.accounts:
            print("Get accounts")
            self.accounts = self.app.get_accounts()

        if not self._check_token_security():
            raise SystemError("The token is not stored safely.")

        self.result = self.app.acquire_token_silent_with_error(
            [self.scope], account=self.accounts[0]
        )

        if "access_token" in self.result:
            print("Token found")
        elif "error" in self.result:
            print("Error getting access token" + self.result["error"])
        else:
            print("Acuire token failed")

        self._set_expiring_date(int(self.result["expires_in"]))
        self._write_cache()

    def _set_expiring_date(self, time_left, threshold=60):
        """
        Defines the access token expiring date. Sets a threshold to update the token before it expires

        Parameter
            time_left: time, in seconds, until the token expires.
            threshold: how many seconds before expiration the token is allowed to be updated.
        """
        self.expiring_date = datetime.datetime.now() + datetime.timedelta(
            seconds=time_left - threshold
        )

    def _cache_available(self):
        if os.path.isfile(self.token_path):
            return True
        return False

    def _check_token_security(self):
        if sys.platform.lower().startswith("win"):
            return True

        access_stats = os.stat(self.token_path)

        return not bool(access_stats.st_mode & (stat.S_IRWXG | stat.S_IRWXO))

    def _oauth_device_code(self):
        flow = self.app.initiate_device_flow(scopes=[self.scope])

        if "user_code" not in flow:
            raise ValueError(
                "Fail to create device flow. Err: %s" % json.dumps(flow, indent=4)
            )
        else:
            print(flow["message"])

        self.result = self.app.acquire_token_by_device_flow(flow)
        try:
            self._set_expiring_date(int(self.result["expires_in"]))
        except KeyError:
            print(self.result)
        self._write_cache()

    def _write_cache(self):
        old_mask = os.umask(0o077)

        dir_path = os.path.dirname(self.token_path)
        os.makedirs(dir_path, exist_ok=True)

        with open(self.token_path, "w") as file:
            file.write(self.cache.serialize())

        if not sys.platform.lower().startswith("win"):
            os.chmod(self.token_path, 0o600)
            os.chmod(dir_path, 0o700)

        os.umask(old_mask)

    def _read_cache(self):
        with open(self.token_path, "r") as file:
            self.cache.deserialize(file.read())

    def _get_cache(self):

        self.cache = msal.SerializableTokenCache()
        if self._cache_available():
            self._read_cache()


if __name__ == "__main__":
    auth = Auth(
        "1826bd7c-582f-4838-880d-5b4da5c3eea2", "88d2b022-3539-4dda-9e66-853801334a86"
    )
    print(auth.get_token())
