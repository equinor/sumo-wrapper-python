from ._call_azure_api import CallAzureApi

class CallSumoSurfaceApi:
    """
        This class can be used for calling the Sumo Surface APi.
    """


    def __init__(self, env='dev'):
        if env == 'prod':
            self.base_url = 'https://main-sumo-surface-proto-prod.playground.radix.equinor.com/api/v1'
        else:
            self.base_url = 'https://main-sumo-surface-proto-dev.playground.radix.equinor.com/api/v1'

        self.resource_id = '88d2b022-3539-4dda-9e66-853801334a86'

        self.callAzureApi = CallAzureApi(self.resource_id)

    def __str__(self):
        sb = []
        for key in self.__dict__:
            sb.append("{key}='{value}'".format(key=key, value=self.__dict__[key]))

        return ', '.join(sb)

    def __repr__(self):
        return self.__str__()

    def get_bear_token(self):
        """
               Generating an Azure OAuth2 bear token.
               You need to open this URL in a web browser https://microsoft.com/devicelogin, and enter the code that is printed.

               Return
                       accessToken:
                           The Bearer Authorization string
        """
        return self.callAzureApi.get_bear_token()

    def search(self, query, select=None, buckets=None, search_from=0, search_size=10, bearer=None):
        """
                 Search for specific objects.

                 Parameters
                    query string, in Lucene search syntax.
                    select string, comma-separated list of fields to return. Default: all fields.
                    buckets string, comma-separated list of fields to build buckets from. Default: none.
                    search_from string, start index for search result (for paging through lare result sets. Default: 0.
                    search_size, int, max number of hits to return. Default: 10.
                    bearer string, Azure OAuth2 bear token Default: will create one.

                Return
                    json:
                        Search results.

        """
        url = f'{self.base_url}/search?$query={query}&$from={search_from}&$size={search_size}&$select={select}'
        if buckets:
            url = f'{url}&$buckets={buckets}'

        return self.callAzureApi.get_json(url, bearer)

    def get_json(self, object_id, bearer=None):
        """
                     Returns the stored json-document for the given objectid.

                     Parameters
                        object_id string, the id for the json document to return.
                        bearer string, Azure OAuth2 bear token Default: will create one.

                    Return
                        json:
                            Json document for the given objectId.
        """
        url = f"{self.base_url}/objects('{object_id}')"
        return self.callAzureApi.get_json(url, bearer)

    def save_top_level_json(self, json, bearer=None):
        """
                     Adds a new top-level json object to SUMO.

                     Parameters
                        json json, Json document to save.
                        bearer string, Azure OAuth2 bear token Default: will create one.

                    Return
                        string:
                            The object_id of the newly updated object.
        """
        return self._post_objects(json=json, bearer=bearer)

    def save_child_level_json(self, object_id, json, bearer=None):
        """
                     Creates a new child object (json document) for the object given by objectId.
                     Fails if objectId does not exist.
                     Also sets the _sumo.parent_object attribute for the new object to point at the parent object.

                     Parameters
                        object_id string, the id of the json object that this json document will be attached to.
                        json json, Json document to save.
                        bearer string, Azure OAuth2 bear token Default: will create one.

                    Return
                        string:
                            The object_id of the newly updated object.
        """
        return self._post_objects(object_id=object_id, json=json, bearer=bearer)

    def get_blob(self, object_id, bearer=None):
        """
                     Get a binary file from blob-storage as a binary-stream for the objectId.

                     Parameters
                        object_id string, the id for the blob document to return.
                        bearer string, Azure OAuth2 bear token Default: will create one.

                    Return
                        binary:
                            Binary-stream for the objectId.
        """
        url = f"{self.base_url}/objects('{object_id}')/blob"
        return self.callAzureApi.get_content(url, bearer)

    def save_blob(self, object_id, blob, bearer=None):
        """
                     Post a binary file to blob storage for the objectId.

                     Parameters
                        object_id string, the id of the json object that this blob document will be attached to.
                        blob binary, the binary to save
                        bearer string, Azure OAuth2 bear token Default: will create one.

                    Return
                        string:
                            The object_id of the newly updated object.
        """
        return self._post_objects(object_id=object_id, blob=blob, bearer=bearer)

    def delete_object(self, object_id, bearer=None):
        """
                     Deletes the stored json-document for the given objectid.

                     Parameters
                        object_id string, the id of the json object that will be deleted.
                        bearer string, Azure OAuth2 bear token Default: will create one.

                    Return
                        json:
                            A json object that includes the id of the deleted object.
        """
        url = f"{self.base_url}/objects('{object_id}')"
        return self.callAzureApi.delete_json(url, bearer)

    def _post_objects(self, object_id=None, blob=None, json=None, bearer=None):
        url = f'{self.base_url}/objects'
        if object_id:
            url = f"{url}('{object_id}')"
        if blob:
            url = f'{url}/blob'

        print(f'\nURL: {url}\n')
        return self.callAzureApi.post(url, blob, json, bearer)

