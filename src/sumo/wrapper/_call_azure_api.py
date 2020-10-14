import requests
from ._auth import Auth
from io import BytesIO, StringIO

class CallAzureApi:
    """
        This class can be used for generating an Azure OAuth2 bear token and send a request to Azure JSON rest endpoint.
        The Azure clientId "1826bd7c-582f-4838-880d-5b4da5c3eea2" need to have permissions to the resourceId that you send inn.


        Parameters
                resourceId:
                    Need to be an Azure resourceId
    """

     # TODO: Should Client ID be hard coded?
    client_id = "1826bd7c-582f-4838-880d-5b4da5c3eea2"
    bearer = None

    def __init__(self, resource_id):
        self.auth = Auth(self.client_id, resource_id)
        self.bearer = "Bearer " + self.auth.get_token()

    def __str__(self):
        str_repr = ["{key}='{value}'".format(key=k, value=v) for k, v in self.__dict__.items()]
        return ', '.join(str_repr)

    def __repr__(self):
        return self.__str__()

    def get_bear_token(self):
        """
            Get an Azure OAuth2 bear token.
            You need to open this URL in a web browser https://microsoft.com/devicelogin, and enter the code that is printed.

            Return
                accessToken:
                    The Bearer Authorization string
        """
        return self.bearer

    def get_json(self, url, bearer=None):
        """
            Send an request to the url.

            Parameters
                url
                    Need to be a Azure rest url that returns a JSON.
                bearer
                    Optional, if not entered it will generate one by calling the get_bear_token method
            
            Return
                json:
                    The json respond from the entered URL
        """   
        if bearer is not None:
            self.bearer = bearer

        headers = {"Content-Type": "application/json",
                   "Authorization": self.bearer}

        response = requests.get(url, headers=headers)

        if not response.ok:
            raise Exception(f'Status code: {response.status_code}, Text: {response.text}')

        return response.json()

    def get_image(self, url, bearer=None):
        """
            Send an request to the url for the image.

            Parameters
                url
                    Need to be a Azure rest url that returns a JSON.
                bearer
                    Optional, if not entered it will generate one by calling the get_bear_token method
            
            Return
                image:
                    raw image
        """
        if bearer is not None:
            self.bearer = bearer

        headers = {"Content-Type": "html/text",
                   "Authorization": self.bearer}

        response = requests.get(url, headers=headers, stream=True)
        
        if response.status_code == 200:
            return response.raw.read()

        return None

    def get_content(self, url, bearer=None):
        """
            Send an request to the url.

            Parameters
                url
                    Need to be a Azure rest url that returns a JSON.
                bearer
                    Optional, if not entered it will generate one by calling the get_bear_token method
            
            Return
               content:
                    The content respond from the entered URL
        """
        if bearer is not None:
            self.bearer = bearer

        headers = {"Content-Type": "application/json",
                   "Authorization": self.bearer}

        response = requests.get(url, headers=headers)

        if not response.ok:
            raise Exception(f'Status code: {response.status_code}, Text: {response.text}')

        return response.content

    def post(self, url, blob=None, json=None, bearer=None):
        """
        Post binary or json to the url and return the response as json.

        Parameters
            url: Need to be a Azure rest url that returns a JSON.
            blob: Optional, the binary to save
            json: Optional, the json to save
            bearer: Optional, if not entered it will generate one by calling the get_bear_token method
        
        Return
            string: The string respond from the entered URL
        """
        if bearer is not None:
            self.bearer = bearer

        if blob and json:
            raise ValueError('Both blob and json given to post - can only have one at the time.')

        headers = {"Content-Type": "application/json" if json is not None else "application/octet-stream",
                   "Authorization": self.bearer,
                   "Content-Length" : str(len(json) if json != None else len(blob)),
                   }

        response = requests.post(url, data=blob, json=json, headers=headers)

        if not response.ok:
           raise Exception(f'Status code: {response.status_code}, Text: {response.text}')

        return response

    def put(self, url, blob=None, json=None, bearer=None):
        """
            Put binary to the url and return the response as json.

            Parameters
                url: Need to be a Azure rest url that returns a JSON.
                blob: Optional, the binary to save
                json: Optional, the json to save
                bearer: Optional, if not entered it will generate one by calling the get_bear_token method
            
            Return
                string: The string respond from the entered URL
        """
        if bearer is not None:
            self.bearer = bearer

        if blob and json:
            raise ValueError('Both blob and json given to post - can only have one at the time.')

        headers = {"Content-Type": "application/json" if json is not None else "application/octet-stream",
                   "Content-Length" : str(len(json) if json != None else len(blob)),
                   "x-ms-blob-type" : "BlockBlob"
                   }

        if url.find("sig=") < 0 :
            headers["Authorization"] = self.bearer

        response = requests.put(url, data=blob, json=json, headers=headers)

        #if not response.ok:
        #    raise Exception(f'Status code: {response.status_code}, Text: {response.text}')

        return response

    
    def delete_object(self, url, bearer=None):
        """
            Send delete to the url and return the response as json.

            Parameters
                url: Need to be a Azure rest url that returns a JSON.
                bearer: Optional, if not entered it will generate one by calling the get_bear_token method
            
            Return
                json: The json respond from the entered URL
        """
        if bearer is not None:
            self.bearer = bearer

        headers = {"Content-Type": "application/json",
                   "Authorization": self.bearer,
                   }

        response = requests.delete(url, headers=headers)

        if not response.ok:
            raise Exception(f'Status code: {response.status_code}, Text: {response.text}')

        return response.json()
