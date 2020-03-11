from adal import AuthenticationContext
import requests


class CallAzureApi:
    '''
        This class can be used for generating an Azure OAuth2 bear token and send a request to Azure JSON rest endpoint.
        The Azure clientId "1826bd7c-582f-4838-880d-5b4da5c3eea2" need to have permissions to the resourceId that you send inn.


        Parameters
                resourceId:
                    Need to be an Azure resourceId
    '''

    tenant = "statoilsrm.onmicrosoft.com"
    authorityHostUrl = "https://login.microsoftonline.com"
    authority_url = (authorityHostUrl + '/' + tenant)

    clientId = "1826bd7c-582f-4838-880d-5b4da5c3eea2"
    bearer = None

    def __init__(self, resourceId):
        self.resourceId = resourceId

    def __str__(self):
        sb = []
        for key in self.__dict__:
            sb.append("{key}='{value}'".format(key=key, value=self.__dict__[key]))

        return ', '.join(sb)

    def __repr__(self):
        return self.__str__()

    '''
        Generating an Azure OAuth2 bear token.
        You need to open this URL in a web browser https://microsoft.com/devicelogin, and enter the code that is printed. 
        
        Return 
                accessToken:
                    The Bearer Authorization string
    '''
    def get_bear_token(self):

        context = AuthenticationContext(self.authority_url, validate_authority=self.tenant, cache=None, api_version=None,
                                        timeout=None, enable_pii=False)
        code = context.acquire_user_code(self.resourceId, self.clientId)

        print(code['message'])

        token = context.acquire_token_with_device_code(self.resourceId, code, self.clientId)
        self.bearer = "Bearer " + token['accessToken']

        return self.bearer

    '''
        Send an request to the url.
        
        Parameters
            url
                Need to be a Azure rest url that returns a JSON.
            bearer
                Optional, if not entered it will generate one by calling the get_bear_token method
        Return 
                json:
                    The json respond from the entered URL
        '''
    def get_json(self, url, bearer=None):
        if bearer is None:
            if self.bearer is None:
                self.get_bear_token()
        else:
            self.bearer = bearer

        headers = {"Content-Type": "application/json",
                   "Authorization": self.bearer}

        response = requests.get(url, headers=headers)

        return response.json()
