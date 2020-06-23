"""Example code for communicating with Sumo"""

import pytest
from sumo.wrapper import CallSumoApi


class Connection:
    def __init__(self):
        self.api = CallSumoApi()
        self.api.get_bear_token()        

def _upload_parent_object(C, json):
    response = C.api.save_top_level_json(json=json)
    if not 200 <= response.status_code < 202:
        raise Exception(f'code: {response.status_code}, text: {response.text}')
    parent_id = response.text
    return parent_id

def _upload_blob(C, object_id, blob):
    response = C.api.save_blob(object_id=object_id, blob=blob)
    if not 200 <= response.status_code < 202:
        raise Exception(f'blob upload to object_id {object_id} returned {response}')    
    return response.text

def _download_object(C, object_id):
    json = C.api.get_json(object_id=object_id)
    return json

def _upload_child_level_json(C, parent_id, json):
    response = C.api.save_child_level_json(object_id=parent_id, json=json)
    if not 200 <= response.status_code < 202:
        raise Exception(response.text)
    child_id = response.text
    return child_id

def _delete_object(C, object_id):
    response = C.api.delete_object(object_id=object_id)
    return response


##### TESTS #####

def test_fail_on_wrong_metadata():
    C = Connection()

    # upload a parent object with erroneous metadata, confirm failure
    json = {"some field": "some value"}
    response = C.api.save_top_level_json(json=json)
    assert response.status_code == 400

def test_sequence():
    C = Connection()
    unique_text = 'ThisIsMyUniqueText'
    b = b'123456789'
    parent_json = {"status": "scratch",
            "field": "JOHAN SVERDRUP",
            "field_guid": 268281971,
            "testdata": 'parent',
            "country_identifier": "Norway",
            "some_parent_metadata": {"field1": "1", "field2": "2"}, 
                "some_ints": {"field3": 3, "field4": 4}, 
                "some_floats": {"field5": 5.0, "field6": 6.0}
                }

    child1_json = {"status": "scratch",
            "field": "JOHAN SVERDRUP",
            "field_guid": 268281971,
            "testdata": 'child1',
            "country_identifier": "Norway",
            "some_child_metadata": {"field1": "1", "field2": "2"}, 
                "some_ints": {"field3": 3, "field4": 4}, 
                "some_floats": {"field5": 5.0, "field6": 6.0}
                }

    child2_json = {"status": "scratch",
            "field": "JOHAN SVERDRUP",
            "field_guid": 268281971,
            "testdata": 'child2',
            "country_identifier": "Norway",
            "some_child_metadata": {"field1": "1", "field2": "2"}, 
                "some_ints": {"field3": 3, "field4": 4}, 
                "some_floats": {"field5": 5.0, "field6": 6.0}
                }


    #upload a parent object, get object_id
    parent_id = _upload_parent_object(C=C, json=parent_json)

    # confirm failure on blob upload to parent object
    with pytest.raises(Exception):
        _upload_blob(C=C, object_id=parent_id, blob=b)

    # upload child object, get child_id
    child1_id = _upload_child_level_json(C=C, parent_id=parent_id, json=child1_json)
    child2_id = _upload_child_level_json(C=C, parent_id=parent_id, json=child2_json)
    assert child1_id != child2_id

    # upload blob on child level
    _upload_blob(C=C, object_id=child1_id, blob=b)
    _upload_blob(C=C, object_id=child2_id, blob=b)

    # get child1 JSON
    objects_results = _download_object(C=C, object_id=child1_id)
    found = objects_results['found']
    if found:
        print('text:')
        print(objects_results)
    else:
        raise Exception(f'Object not found : {found}')

    # search for child1, get one hit
    search_results = C.api.search(query='child1')
    hits = search_results.get('hits').get('hits')
    total = search_results.get('hits').get('total').get('value')
    assert total == 1
    assert len(hits) == 1

    # search for child2, get one hit
    search_results = C.api.search(query='child2')
    hits = search_results.get('hits').get('hits')
    total = search_results.get('hits').get('total').get('value')
    assert total == 1
    assert len(hits) == 1

    # delete child2
    result = _delete_object(C=C, object_id=child2_id)
    assert result == 'ok'

    # search for child2, get zero hits
    search_results = C.api.search(query='child2')
    hits = search_results.get('hits').get('hits')
    total = search_results.get('hits').get('total').get('value')
    assert total == 0
    assert len(hits) == 0

    # delete parent
    result = _delete_object(C=C, object_id=parent_id)
    assert result == 'ok'

    # search for child1, get zero hits
    search_results = C.api.search('testdata:child1')
    hits = search_results.get('hits').get('hits')
    total = search_results.get('hits').get('total').get('value')
    assert total == 0
    assert len(hits) == 0

