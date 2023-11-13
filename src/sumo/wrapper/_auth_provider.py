import msal
import os
from datetime import datetime, timedelta
import stat
import sys
import json
import jwt
import time
from azure.identity import ManagedIdentityCredential

from msal_extensions.persistence import FilePersistence
from msal_extensions.token_cache import PersistedTokenCache

if not sys.platform.startswith("linux"):
    from msal_extensions import build_encrypted_persistence


def scope_for_resource(resource_id):
    return f"{resource_id}/.default"


class AuthProvider:
    def __init__(self, resource_id):
        self._resource_id = resource_id
        self._scope = scope_for_resource(resource_id)
        self._app = None
        return

    def get_token(self):
        accounts = self._app.get_accounts()
        if len(accounts) == 0:
            return None
        result = self._app.acquire_token_silent([self._scope], accounts[0])
        if result is None:
            return None
        # ELSE
        return result["access_token"]

    pass


class AuthProviderAccessToken(AuthProvider):
    def __init__(self, access_token):
        self._access_token = access_token
        payload = jwt.decode(access_token, options={"verify_signature": False})
        self._expires = payload["exp"]
        return

    def get_token(self):
        if time.time() >= self._expires:
            raise ValueError("Access token has expired.")
        # ELSE
        return self._access_token

    pass


class AuthProviderRefreshToken(AuthProvider):
    def __init__(self, refresh_token, client_id, authority, resource_id):
        super().__init__(resource_id)
        self._app = msal.PublicClientApplication(
            client_id=client_id, authority=authority
        )
        self._scope = scope_for_resource(resource_id)
        self._app.acquire_token_by_refresh_token(refresh_token, [self._scope])
        return

    pass


def get_token_path(resource_id):
    return os.path.join(
        os.path.expanduser("~"), ".sumo", str(resource_id) + ".token"
    )


def get_token_cache(resource_id):
    # https://github.com/AzureAD/microsoft-authentication-extensions-\
    # for-python
    # Encryption not supported on linux servers like rgs, and
    # neither is common usage from many cluster nodes.
    # Encryption is supported on Windows and Mac.

    cache = None
    token_path = get_token_path(resource_id)
    if sys.platform.startswith("linux"):
        persistence = FilePersistence(token_path)
        cache = PersistedTokenCache(persistence)
    else:
        if os.path.exists(token_path):
            encrypted_persistence = build_encrypted_persistence(token_path)
            try:
                token = encrypted_persistence.load()
            except Exception:
                # This code will encrypt an unencrypted existing file
                token = FilePersistence(token_path).load()
                with open(token_path, "w") as f:
                    f.truncate()
                    pass
                encrypted_persistence.save(token)
                pass
            pass

        persistence = build_encrypted_persistence(token_path)
        cache = PersistedTokenCache(persistence)
        pass
    return cache


def protect_token_cache(resource_id):
    token_path = get_token_path(resource_id)

    if sys.platform.startswith("linux"):
        filemode = stat.filemode(os.stat(token_path).st_mode)
        if filemode != "-rw-------":
            os.chmod(token_path, 0o600)
            folder = os.path.dirname(token_path)
            foldermode = stat.filemode(os.stat(folder).st_mode)
            if foldermode != "drwx------":
                os.chmod(os.path.dirname(token_path), 0o700)
                pass
            pass
        return
    pass


class AuthProviderInteractive(AuthProvider):
    def __init__(self, client_id, authority, resource_id):
        super().__init__(resource_id)
        cache = get_token_cache(resource_id)
        self._app = msal.PublicClientApplication(
            client_id=client_id, authority=authority, token_cache=cache
        )
        self._resource_id = resource_id

        self._scope = scope_for_resource(resource_id)

        if self.get_token() is None:
            self.login()
            pass
        return

    def login(self):
        scopes = [self._scope + " offline_access"]
        login_timeout_minutes = 7
        os.system("")  # Ensure color init on all platforms (win10)
        print(
            "\n\n \033[31m NOTE! \033[0m"
            + " Please login to Equinor Azure to enable Sumo access: "
            + "we opened a login web-page for you in your browser."
            + "\nYou should complete your login within "
            + str(login_timeout_minutes)
            + " minutes, "
            + "that is before "
            + str(
                (
                    datetime.now() + timedelta(minutes=login_timeout_minutes)
                ).strftime("%H:%M:%S")
            )
        )
        try:
            result = self._app.acquire_token_interactive(
                scopes, timeout=(login_timeout_minutes * 60)
            )
            if "error" in result:
                print(
                    "\n\n \033[31m Error during Equinor Azure login "
                    "for Sumo access: \033[0m"
                )
                print("Err: ", json.dumps(result, indent=4))
                return
        except Exception:
            print(
                "\n\n \033[31m Failed Equinor Azure login for Sumo access, "
                "one possible reason is timeout \033[0m"
            )
            return

        protect_token_cache(self._resource_id)
        print("Equinor Azure login for Sumo access was successful")
        return

    pass


class AuthProviderManaged(AuthProvider):
    def __init__(self, resource_id):
        super().__init__(resource_id)
        self._app = ManagedIdentityCredential()
        self._scope = scope_for_resource(resource_id)
        return

    def get_token(self):
        return self._app.get_token(self._scope).token

    pass


def get_auth_provider(
    client_id,
    authority,
    resource_id,
    interactive=False,
    access_token=None,
    refresh_token=None,
):
    if refresh_token:
        return AuthProviderRefreshToken(
            refresh_token, client_id, authority, resource_id
        )
    # ELSE
    if access_token:
        return AuthProviderAccessToken(access_token)
    # ELSE
    if interactive:
        return AuthProviderInteractive(client_id, authority, resource_id)

    # ELSE
    if all(
        [
            os.getenv(x)
            for x in [
                "AZURE_FEDERATED_TOKEN_FILE",
                "AZURE_TENANT_ID",
                "AZURE_CLIENT_ID",
                "AZURE_AUTHORITY_HOST",
            ]
        ]
    ):
        return AuthProviderManaged(resource_id)

    # ELSE
    # Device code login does not work with Equinor compliant device policy
    # return AuthProviderDeviceCode(client_id, authority, resource_id)
    return AuthProviderInteractive(client_id, authority, resource_id)
