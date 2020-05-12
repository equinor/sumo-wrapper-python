import msal
import os, json
TENANT = "3aa4a235-b6e2-48d5-9195-7fcf05b459b0"

AUTHORITY_HOST_URI = 'https://login.microsoftonline.com'
AUTHORITY_URI = AUTHORITY_HOST_URI + '/' + TENANT
HOME_DIR = os.path.expanduser('~')


class Auth():

    def __init__(self, client_id, resource_id, authority=AUTHORITY_URI, client_crediatials=None):
        self.client_id = client_id
        self.resource_id = resource_id
        self.scope = self.resource_id + "/.default"
        self.authority = authority
        self.client_crediatials = client_crediatials
        self.token_path = os.path.join(HOME_DIR, ".omnia", str(self.resource_id) + ".token")
        self._get_cache()
        self.app = msal.PublicClientApplication(self.client_id, authority=AUTHORITY_URI,
                                                client_credential=self.client_crediatials, token_cache=self.cache)
        self.accounts = self.app.get_accounts()
        self._oauth_get_token_silent() if self._cache_availible() else self._oauth_device_code()

    def get_token(self):
        self._oauth_get_token_silent()
        return self.result["access_token"]

    def _oauth_get_token_silent(self):
        if not self.accounts:
            self.accounts = self.app.get_accounts()
        self.result = self.app.acquire_token_silent([self.scope], account=self.accounts[0])
        self._write_cache()

    def _cache_availible(self):
        if os.path.isfile(self.token_path):
            return True
        return False

    def _oauth_device_code(self):
        flow = self.app.initiate_device_flow(scopes=[self.scope])

        if "user_code" not in flow:
            raise ValueError(
                "Fail to create device flow. Err: %s" % json.dumps(flow, indent=4))

        self.result = self.app.acquire_token_by_device_flow(flow)
        self._write_cache()

    def _write_cache(self):
        os.makedirs(os.path.dirname(self.token_path), exist_ok=True)
        with open(self.token_path, "w") as file:
            file.write(self.cache.serialize())

    def _read_cache(self):
        self.cache.deserialize(open(self.token_path, "r").read())

    def _get_cache(self):

        self.cache = msal.SerializableTokenCache()
        if self._cache_availible():
            self._read_cache()