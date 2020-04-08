from sumo_surface_python.call_sumo_surface_api import CallSumoSurfaceApi


class TestCallSumoSurfaceApi:

    def __init__(self):
        self.api = CallSumoSurfaceApi()
        self.api.get_bear_token()

    def save_json(self):
        json = {"surfacename": "ones", "some_metadata": {"field1": "1", "field2": "2"}, "some_ints": {"field3": 3, "field4": 4}, "some_floats": {"field5": 5.0, "field6": 6.0}}
        object_id = self.api.save_top_level_json(json=json)
        return object_id

    def save_blob(self, object_id):
        b = b'123456789'
        object_id = self.api.save_blob(object_id=object_id, blob=b)
        return object_id

    def get_json(self, object_id):
        objects_results = self.api.get_json(object_id)
        found = objects_results['found']
        if found:
            return objects_results['_id']
        else:
            raise Exception(f'Object not found : {found}')

    def get_blob(self, object_id):
        objects_results = self.api.get_blob(object_id)
        str_results = objects_results.decode('utf-8');
        if str_results != '123456789':
            raise Exception(f'blob is : {str_results}')

    def delete_object(self, object_id):
        results = self.api.delete_object(object_id)
        result = results['result']
        if result == 'deleted':
            return results['_id']
        else:
            raise Exception(f'Object not deleted : {result}')

    def search(self):
        search_results = self.api.get_search('name=Lindvar', 'name,age,car')
        return search_results['hits']['total']['value']


if __name__ == '__main__':

    test = TestCallSumoSurfaceApi()

    print('****** START ******')
    object_id = test.save_json()
    print(f'save_json return id: {object_id}')

    object_id_blob = test.save_blob(object_id)
    print(f'save_blob on id: {object_id_blob}')

    test.get_json(object_id)
    print(f'get_json for id: {object_id}')

    test.get_blob(object_id)
    print(f'get_blob for id: {object_id}')

    ant = test.search()
    print(f'search return: {ant} items')

    test.delete_object(object_id)
    print(f'delete_object id: {object_id}')

    print('****** END ******')


