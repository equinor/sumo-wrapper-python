from ._call_sumo_surface_api import CallSumoSurfaceApi

class SumoConnection:
    """Object to hold authentication towards Sumo"""

    def __init__(self):
        self._api = None

    @property
    def api(self):
        if self._api is None:
            self._api = self._establish_connection()
            name = self._api.userdata.get('name')
            upn = self._api.userdata.get('upn')
            print(f"Authenticated user: {name} ({upn})")

        return self._api

    def refresh(self):
        """Re-create the connection"""
        self._api = self._establish_connection()        

    def _establish_connection(self):
        """Establish the connection with Sumo API, take user through 2FA."""

        print('establish connection')
        api = CallSumoSurfaceApi()
        api.get_bear_token()

        print('done')

        return api
