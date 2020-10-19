from ._call_azure_api import CallAzureApi

class CallSumoApi:
    """
        This class can be used for calling the Sumo APi.
    """

    def __init__(self, env='dev'):
        """ Initialize the wrapper. Chooses among multiple environments."""
        if env == 'exp':
            self.base_url = 'https://main-sumo-experiment-dev.playground.radix.equinor.com/api/v1'
        elif env == 'localhost':
            self.base_url = f'http://localhost:8084/api/v1'
        else:
            self.base_url = f'https://main-sumo-{env}.radix.equinor.com/api/v1'

        # TODO: Should Resource ID be hard coded?
        self.resource_id = '88d2b022-3539-4dda-9e66-853801334a86'
        self.callAzureApi = CallAzureApi(self.resource_id)

    def __str__(self):
        str_repr = ["{key}='{value}'".format(key=k, value=v) for k, v in self.__dict__.items()]
        return ', '.join(str_repr)

    def __repr__(self):
        return self.__str__()

    @property
    def userdata(self):
        """Get user data from Sumo endpoint /userdata"""
        url = f"{self.base_url}/userdata"
        return self.callAzureApi.get_json(url)

    @property
    def userphoto(self):
        """Get user photo from Sumo endpoint /userphoto"""
        url = f"{self.base_url}/userphoto"
        return self.callAzureApi.get_image(url)

    @property
    def userprofile(self):
        """Get user profile from Sumo endpoint /userprofile"""
        url = f"{self.base_url}/userprofile"
        return self.callAzureApi.get_json(url)

    # For discussion: Do we need to print the code and expect the user to manually type it on the browser or is there a better way to do it
    def get_bearer_token(self):
        """
            Generating an Azure OAuth2 bear token.
            You need to open this URL in a web browser https://microsoft.com/devicelogin, and enter the code that is printed.

            Return
                accessToken:
                    The Bearer Authorization string
        """
        return self.callAzureApi.get_bearer_token()

    def search(self, query, select=None, buckets=None, search_from=0, search_size=100, bearer=None):
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
        url = f'{self.base_url}/search?$query={query}'
        
        if search_from is not None:
            url = f'{url}&$from={search_from}'
        if search_size is not None:
            url = f'{url}&$size={search_size}'
        if select:
            url = f'{url}&$select={select}'
        if buckets:
            url = f'{url}&$buckets={buckets}'

        return self.callAzureApi.get_json(url, bearer)

    def searchroot(self, query, select=None, buckets=None, search_from=0, search_size=100, bearer=None):
        """
            Search for parent objects (object without parent)
        """
        url = f'{self.base_url}/searchroot?$query={query}'

        if search_from is None:
            search_from = 0
        url = f'{url}&$from={search_from}'
        
        if search_size is None:
            search_size = 100
        url = f'{url}&$size={search_size}'
        
        if select:
            url = f'{url}&$select={select}'
        if buckets:
            url = f'{url}&$buckets={buckets}'

        return self.callAzureApi.get_json(url, bearer)

    def get_objects(self, bearer=None):
        """
            Returns a list with all stored JSON objects.

            Parameters
                bearer string, Azure OAuth2 bear token Default: will create one.

            Return
                list:
                    list of objects.
        """
        url = f"{self.base_url}/Objects"
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
                    The object_id of the newly created object.
        """
        return self._post_objects(json=json, bearer=bearer)

    def update_top_level_json(self, json, object_id=None, url=None, bearer=None):
        """
            Updates a top-level json object in SUMO.

            Parameters
                json: json, JSON documents to save.
                object_id: string, the ID of the object to be modified.
                url: string, the url where the JSON is stored. When not None, it overrides object ID
                bearer: string, Azure OAuth2 bear token Default: will create one.
        """
        if not object_id and not url:
            raise ValueError('Error: object ID and url cannot be both null.')

        return self._put_objects(json, object_id=object_id, url=url, bearer=bearer)

    def save_child_level_json(self, parent_id, json, bearer=None):
        """
            Creates a new child object (json document) for the object given by objectId.
            Fails if objectId does not exist.
            Also sets the _sumo.parent_object attribute for the new object to point at the parent object.

            Parameters
                parent_id: string, the id of the json object that this json document will be attached to.
                json: json, JSON document to save.
                bearer: string, Azure OAuth2 bear token Default: will create one.

            Return
                string: The object id of the newly created object, or error message.
        """
        return self._post_objects(object_id=parent_id, json=json, bearer=bearer)

    def update_child_level_json(self, json, object_id=None, url=None, bearer=None):
        """
            Updates a child-level json object in SUMO.

            Parameters
                json: json, JSON documents to save.
                object_id: string, the ID of the object to be modified.
                url: string, the url where the JSON is stored. When not None, it overrides object ID
                bearer: string, Azure OAuth2 bear token Default: will create one.
        """
        if not object_id and not url:
            raise ValueError('Error: object ID and url cannot be both null.')

        return self._put_objects(json, object_id=object_id, url=url, bearer=bearer)


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
        return self.callAzureApi.delete_object(url, bearer)

    def save_blob(self, blob, object_id=None, bearer=None, url=None):
        """
            Save a binary file to blob storage.

            Parameters
                object_id: string, the id of the json object that this blob document will be attached to.
                blob: binary, the binary to save
                bearer: string, Azure OAuth2 bear token Default: will create one.

        """
        return self._post_objects(object_id=object_id, blob=blob, bearer=bearer, url=url)

    def update_blob(self, blob, object_id=None, bearer=None, url=None):
        """
            Put a binary file to blob storage for the objectId.

            Parameters
                object_id string, the id of the json object that this blob document will be attached to.
                blob binary, the binary to save
                bearer string, Azure OAuth2 bear token Default: will create one.

            Return
                string:
                    The object_id of the newly updated object.
        """
        return self._put_objects(object_id=object_id, blob=blob, bearer=bearer, url=url)


    def get_blob(self, object_id, bearer=None):
        """
            Get a binary file from blob-storage as a binary-stream for the objectId.

            Parameters
                object_id string, the id for the blob document to return.
                bearer string, Azure OAuth2 bear token Default: will create one.

            Return
                binary: Binary-stream for the objectId.
        """
        url = f"{self.base_url}/objects('{object_id}')/blob"
        return self.callAzureApi.get_content(url, bearer)

    def delete_blob(self, object_id, bearer=None):
        """
            Deletes the stored blob for the given objectid.

            Parameters
                object_id string, the id of the blob object that will be deleted.
                bearer string, Azure OAuth2 bear token Default: will create one.

            Return
                json:
                    A json object that includes the id of the deleted object.
        """
        url = f"{self.base_url}/objects('{object_id}')/blob"
        return self.callAzureApi.delete_object(url, bearer)
    
    def get_blob_uri(self, object_id, bearer=None):
        """
           Get the redirect uri to blob storage for uploading a blob
           Parameters
                object_id string, the id of the json object that will be deleted.
                bearer string, Azure OAuth2 bear token Default: will create one.

            Return
                string:
        """
        url = f"{self.base_url}/objects('{object_id}')/blob/$puturi"
        return self.callAzureApi.get_content(url, bearer)

    def _post_objects(self, json, blob=None, object_id=None, bearer=None):
        """
            Post a new object into sumo.
        
            Parameters
                json: JSON dictionary, containing the object's metadata
                blob: binary, the binary data linked to the object
                object_id: string, the id of the json object this object will be attached to.
                bearer: string, Azure OAuth2 bear token Default: will create one.

            Return
                The object_id of the newly uploaded object, or error message.
        """
        url = f'{self.base_url}/objects'

        if object_id:
            url = f"{url}('{object_id}')"

        if blob:
            url = f'{url}/blob'

        return self.callAzureApi.post(url=url, blob=blob, json=json, bearer=bearer)

    def _put_objects(self, object_id=None, blob=None, json=None, bearer=None, url=None):
        """
            Post a new object into sumo.
            Parameters
                object_id: string, the id of object being updated.
                blob: binary, the binary data linked to the object
                json: JSON dictionary, containing the object's metadata
                bearer: string, Azure OAuth2 bear token Default: will create one.

            Return
                The parent_id of the newly uploaded object, or error message.
        """
        if url is None:
            url = f'{self.base_url}/objects'

            if object_id:
                url = f"{url}('{object_id}')"
            
            if blob:
                url = f'{url}/blob'
        
        return self.callAzureApi.put(url=url, blob=blob, json=json, bearer=bearer)

