import msal
import os
import stat
import sys
import json
import logging
from .config import AUTHORITY_HOST_URI
from msal_extensions.persistence import FilePersistence
from msal_extensions.token_cache import PersistedTokenCache

if not sys.platform.startswith("linux"):
    from msal_extensions import build_encrypted_persistence

HOME_DIR = os.path.expanduser("~")

logger = logging.getLogger("sumo.wrapper")


class NewAuth:
    """Sumo connection

    Establish a connection with a Sumo environment.

    Attributes:
        client_id: App registration id
        resource_id: App registration resource id
        tenant_id: AD tenant
        interactive: Enable interactive authentication (in browser)
        refresh_token: Use outside refresh token to acquire access token
        verbosity: Logging level
    """

    def __init__(
        self,
        client_id,
        resource_id,
        tenant_id,
        interactive=False,
        refresh_token=None,
        verbosity="CRITICAL",
    ):
        logger.setLevel(verbosity)

        self.interactive = interactive
        self.scope = resource_id + "/.default"
        self.refresh_token = refresh_token

        token_path = os.path.join(
            HOME_DIR, ".sumo", str(resource_id) + ".token"
        )
        self.token_path = token_path

        # https://github.com/AzureAD/microsoft-authentication-extensions-\
        # for-python
        # Encryption not supported on linux servers like rgs, and
        # neither is common usage from many cluster nodes.
        # Encryption is supported on Windows and Mac.

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

        self.msal = msal.PublicClientApplication(
            client_id=client_id,
            authority=f"{AUTHORITY_HOST_URI}/{tenant_id}",
            token_cache=cache,
        )

    def get_token(self):
        """Gets a token.

        Will first attempt to retrieve a token silently.
        If a user provided refresh token exists,
        attempt to aquire token by refresh token.

        If we are unable to retrieve a token silently and
        no refresh token has been provided by the caller,
        we either initiate a device flow or interactive flow
        based on the `interactive` attribute.

        Returns:
            A Json Web Token
        """

        accounts = self.msal.get_accounts()
        result = None

        if accounts:
            result = self.msal.acquire_token_silent(
                [self.scope], account=accounts[0]
            )

        if not result:
            if self.refresh_token:
                result = self.msal.acquire_token_by_refresh_token(
                    self.refresh_token, [self.scope]
                )

                if "error" in result:
                    raise ValueError(
                        "Failed to acquire token by refresh token. Err: %s"
                        % json.dumps(result, indent=4)
                    )
            else:
                if self.interactive:
                    result = self.msal.acquire_token_interactive([self.scope])

                    if "error" in result:
                        raise ValueError(
                            "Failed to acquire token interactively. Err: %s"
                            % json.dumps(result, indent=4)
                        )
                else:
                    flow = self.msal.initiate_device_flow([self.scope])

                    if "error" in flow:
                        raise ValueError(
                            "Failed to create device flow. Err: %s"
                            % json.dumps(flow, indent=4)
                        )

                    print(flow["message"])
                    result = self.msal.acquire_token_by_device_flow(flow)

                    if "error" in result:
                        raise ValueError(
                            "Failed to acquire token by device flow. Err: %s"
                            % json.dumps(result, indent=4)
                        )

        if sys.platform.startswith("linux"):
            filemode = stat.filemode(os.stat(self.token_path).st_mode)
            if filemode != "-rw-------":
                os.chmod(self.token_path, 0o600)
            folder = os.path.dirname(self.token_path)
            foldermode = stat.filemode(os.stat(folder).st_mode)
            if foldermode != "drwx------":
                os.chmod(os.path.dirname(self.token_path), 0o700)

        return result["access_token"]


if __name__ == "__main__":
    auth = NewAuth(
        "1826bd7c-582f-4838-880d-5b4da5c3eea2",
        "88d2b022-3539-4dda-9e66-853801334a86",
        "3aa4a235-b6e2-48d5-9195-7fcf05b459b0",
        interactive=True,
    )
    print(auth.get_token())
