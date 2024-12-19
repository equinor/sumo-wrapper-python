import errno
import json
import os
import stat
import sys
import time
from datetime import datetime, timedelta

import jwt
import msal
import tenacity as tn
from azure.identity import ManagedIdentityCredential
from msal_extensions.persistence import FilePersistence
from msal_extensions.token_cache import PersistedTokenCache

from ._retry_strategy import _log_retry_info, _return_last_value

if not sys.platform.startswith("linux"):
    from msal_extensions import build_encrypted_persistence


def scope_for_resource(resource_id):
    return f"{resource_id}/.default"


def _maybe_nfs_exception(exception):
    return isinstance(exception, OSError) and (
        exception.errno in (errno.EAGAIN, errno.ESTALE)
    )


class AuthProvider:
    def __init__(self, resource_id):
        self._resource_id = resource_id
        self._scope = scope_for_resource(resource_id)
        self._app = None
        self._login_timeout_minutes = 5
        os.system("")  # Ensure color init on all platforms (win10)

        return

    @tn.retry(
        retry=tn.retry_if_exception(_maybe_nfs_exception),
        stop=tn.stop_after_attempt(6),
        wait=(
            tn.wait_exponential(multiplier=0.5, exp_base=2)
            + tn.wait_random_exponential(multiplier=0.5, exp_base=2)
        ),
        retry_error_callback=_return_last_value,
        before_sleep=_log_retry_info,
    )
    def get_token(self):
        accounts = self._app.get_accounts()
        if len(accounts) == 0:
            return None
        result = self._app.acquire_token_silent([self._scope], accounts[0])
        if result is None:
            return None
        # ELSE
        return result["access_token"]

    def get_authorization(self):
        token = self.get_token()
        if token is None:
            return ""

        return {"Authorization": "Bearer " + token}

    def store_shared_access_key_for_case(self, case_uuid, token):
        with open(
            get_token_path(self._resource_id + "+" + case_uuid, ".sharedkey"),
            "w",
        ) as f:
            f.write(token)

    pass


class AuthProviderSilent(AuthProvider):
    def __init__(self, client_id, authority, resource_id):
        super().__init__(resource_id)
        cache = get_token_cache(resource_id, ".token")
        self._app = msal.PublicClientApplication(
            client_id=client_id, authority=authority, token_cache=cache
        )
        self._resource_id = resource_id

        self._scope = scope_for_resource(resource_id)


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


def get_token_path(resource_id, suffix):
    return os.path.join(
        os.path.expanduser("~"), ".sumo", str(resource_id) + suffix
    )


@tn.retry(
    retry=tn.retry_if_exception(_maybe_nfs_exception),
    stop=tn.stop_after_attempt(6),
    wait=(
        tn.wait_exponential(multiplier=0.5, exp_base=2)
        + tn.wait_random_exponential(multiplier=0.5, exp_base=2)
    ),
    retry_error_callback=_return_last_value,
    before_sleep=_log_retry_info,
)
def get_token_cache(resource_id, suffix):
    # https://github.com/AzureAD/microsoft-authentication-extensions-\
    # for-python
    # Encryption not supported on linux servers like rgs, and
    # neither is common usage from many cluster nodes.
    # Encryption is supported on Windows and Mac.

    cache = None
    token_path = get_token_path(resource_id, suffix)
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


@tn.retry(
    retry=tn.retry_if_exception(_maybe_nfs_exception),
    stop=tn.stop_after_attempt(6),
    wait=(
        tn.wait_exponential(multiplier=0.5, exp_base=2)
        + tn.wait_random_exponential(multiplier=0.5, exp_base=2)
    ),
    retry_error_callback=_return_last_value,
    before_sleep=_log_retry_info,
)
def protect_token_cache(resource_id, suffix):
    token_path = get_token_path(resource_id, suffix)

    if sys.platform.startswith("linux") or sys.platform == "darwin":
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
        cache = get_token_cache(resource_id, ".token")
        self._app = msal.PublicClientApplication(
            client_id=client_id, authority=authority, token_cache=cache
        )
        self._resource_id = resource_id

        self._scope = scope_for_resource(resource_id)

        if self.get_token() is None:
            self.login()
            pass
        return

    @tn.retry(
        retry=tn.retry_if_exception(_maybe_nfs_exception),
        stop=tn.stop_after_attempt(6),
        wait=(
            tn.wait_exponential(multiplier=0.5, exp_base=2)
            + tn.wait_random_exponential(multiplier=0.5, exp_base=2)
        ),
        retry_error_callback=_return_last_value,
        before_sleep=_log_retry_info,
    )
    def login(self):
        scopes = [self._scope + " offline_access"]
        print(
            "\n\n \033[31m NOTE! \033[0m"
            + " Please login to Equinor Azure to enable Sumo access: "
            + "we are opening a login web-page for you in your browser."
            + "\nYou should complete your login within "
            + str(self._login_timeout_minutes)
            + " minutes, "
            + "that is before "
            + str(
                (
                    datetime.now()
                    + timedelta(minutes=self._login_timeout_minutes)
                ).strftime("%H:%M:%S")
            )
        )
        try:
            result = self._app.acquire_token_interactive(
                scopes, timeout=(self._login_timeout_minutes * 60)
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

        protect_token_cache(self._resource_id, ".token")
        print(
            "Equinor Azure login for Sumo access was successful (interactive)"
        )
        return

    pass


class AuthProviderDeviceCode(AuthProvider):
    def __init__(self, client_id, authority, resource_id):
        super().__init__(resource_id)
        cache = get_token_cache(resource_id, ".token")
        self._app = msal.PublicClientApplication(
            client_id=client_id, authority=authority, token_cache=cache
        )
        self._resource_id = resource_id
        self._scope = scope_for_resource(resource_id)
        if self.get_token() is None:
            self.login()
            pass
        return

    @tn.retry(
        retry=tn.retry_if_exception(_maybe_nfs_exception),
        stop=tn.stop_after_attempt(6),
        wait=(
            tn.wait_exponential(multiplier=0.5, exp_base=2)
            + tn.wait_random_exponential(multiplier=0.5, exp_base=2)
        ),
        retry_error_callback=_return_last_value,
        before_sleep=_log_retry_info,
    )
    def login(self):
        try:
            scopes = [self._scope + " offline_access"]
            flow = self._app.initiate_device_flow(scopes)
            if "error" in flow:
                print(
                    "\n\n \033[31m"
                    + "Failed to initiate device-code login. Err: %s"
                    + "\033[0m" % json.dumps(flow, indent=4)
                )
                return
            flow["expires_at"] = (
                int(time.time()) + self._login_timeout_minutes * 60
            )

            print(
                "\033[31m"
                + " NOTE! Please login to Equinor Azure to enable Sumo access:"
                + flow["message"]
                + " \033[0m"
                + "\nYou should complete your login within a few minutes"
            )
            result = self._app.acquire_token_by_device_flow(flow)

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

        protect_token_cache(self._resource_id, ".token")
        print(
            "Equinor Azure login for Sumo access was successful (device-code)"
        )

        return

    pass


class AuthProviderManaged(AuthProvider):
    def __init__(self, resource_id):
        super().__init__(resource_id)
        self._app = ManagedIdentityCredential()
        self._scope = scope_for_resource(resource_id)
        return

    @tn.retry(
        retry=tn.retry_if_exception(_maybe_nfs_exception),
        stop=tn.stop_after_attempt(6),
        wait=(
            tn.wait_exponential(multiplier=0.5, exp_base=2)
            + tn.wait_random_exponential(multiplier=0.5, exp_base=2)
        ),
        retry_error_callback=_return_last_value,
        before_sleep=_log_retry_info,
    )
    def get_token(self):
        return self._app.get_token(self._scope).token

    pass


class AuthProviderSumoToken(AuthProvider):
    @tn.retry(
        retry=tn.retry_if_exception(_maybe_nfs_exception),
        stop=tn.stop_after_attempt(6),
        wait=(
            tn.wait_exponential(multiplier=0.5, exp_base=2)
            + tn.wait_random_exponential(multiplier=0.5, exp_base=2)
        ),
        retry_error_callback=_return_last_value,
        before_sleep=_log_retry_info,
    )
    def __init__(self, resource_id):
        protect_token_cache(resource_id, ".sharedkey")
        token_path = get_token_path(resource_id, ".sharedkey")
        with open(token_path, "r") as f:
            self._token = f.readline().strip()
        return

    def get_token(self):
        return self._token

    def get_authorization(self):
        return {"X-SUMO-Token": self._token}


@tn.retry(
    retry=tn.retry_if_exception(_maybe_nfs_exception),
    stop=tn.stop_after_attempt(6),
    wait=(
        tn.wait_exponential(multiplier=0.5, exp_base=2)
        + tn.wait_random_exponential(multiplier=0.5, exp_base=2)
    ),
    retry_error_callback=_return_last_value,
    before_sleep=_log_retry_info,
)
def get_auth_provider(
    client_id,
    authority,
    resource_id,
    interactive=False,
    access_token=None,
    refresh_token=None,
    devicecode=False,
    case_uuid=None,
):
    if refresh_token:
        return AuthProviderRefreshToken(
            refresh_token, client_id, authority, resource_id
        )
    # ELSE
    if access_token:
        return AuthProviderAccessToken(access_token)
    # ELSE
    if case_uuid is not None and os.path.exists(
        get_token_path(resource_id + "+" + case_uuid, ".sharedkey")
    ):
        return AuthProviderSumoToken(resource_id + "+" + case_uuid)
    # ELSE
    if os.path.exists(get_token_path(resource_id, ".sharedkey")):
        return AuthProviderSumoToken(resource_id)
    # ELSE
    if os.path.exists(get_token_path(resource_id, ".token")):
        auth_silent = AuthProviderSilent(client_id, authority, resource_id)
        token = auth_silent.get_token()
        if token is not None:
            return auth_silent
        pass
    # ELSE
    if interactive:
        return AuthProviderInteractive(client_id, authority, resource_id)
    # ELSE
    if devicecode:
        # Potential issues with device-code
        # under Equinor compliant device policy
        return AuthProviderDeviceCode(client_id, authority, resource_id)
    # ELSE
    if all(
        os.getenv(x)
        for x in [
            "AZURE_FEDERATED_TOKEN_FILE",
            "AZURE_TENANT_ID",
            "AZURE_CLIENT_ID",
            "AZURE_AUTHORITY_HOST",
        ]
    ):
        return AuthProviderManaged(resource_id)
