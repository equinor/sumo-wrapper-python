from sumo.call_azure_api import CallAzureApi


class CallSumoSurfaceApi:
    '''
        This class can be used for calling the Sumo Surface APi.
    '''

    dev_resource_id = "88d2b022-3539-4dda-9e66-853801334a86/Read"

    def __init__(self):
        self.callAzureApi = CallAzureApi(self.dev_resource_id);

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
        return self.callAzureApi.get_bear_token()

    '''
         Not implemented yet.
    '''
    def get_health_json(self, bearer=None):
        url = "https://........"
        return self.callAzureApi.get_json(url, bearer)

