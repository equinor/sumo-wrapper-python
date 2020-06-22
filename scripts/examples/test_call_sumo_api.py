"""Example code for communicating with Sumo"""

import pytest
from sumo.wrapper import CallSumoApi


class Connection:
    def __init__(self):
        self.api = CallSumoApi()
        self.api.get_bear_token()        


def _upload_parent_object(C, json):
    response = C.api.save_top_level_json(json=json)
    if response.status_code != 200:
        raise Exception(response.text)
    parent_id = response.text
    return parent_id

def _upload_blob(C, object_id, blob):
    response = C.api.save_blob(object_id=object_id, blob=blob)
    if response.status_code != 200:
        raise Exception(f'blob upload to object_id {object_id} returned {response}')    
    return response.text

def _download_object(C, object_id):
    json = C.get_json(object_id=object_id)
    return json

def _upload_child_level_json(C, parent_id, json):
    response = C.api.save_child_level_json(object_id=parent_id, json=json)
    if response.status_code != 200:
        raise Exception(response.text)
    child_id = response.text
    return child_id


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
            "testdata_uniquetext": unique_text,
            "country_identifier": "Norway",
            "some_parent_metadata": {"field1": "1", "field2": "2"}, 
                "some_ints": {"field3": 3, "field4": 4}, 
                "some_floats": {"field5": 5.0, "field6": 6.0}
                }
    child_json = {"status": "scratch",
            "field": "JOHAN SVERDRUP",
            "field_guid": 268281971,
            "testdata_uniquetext": unique_text,
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
    child_id = _upload_child_level_json(C=C, parent_id=parent_id, json=child_json)

    # upload blob on child level object
    result = _upload_blob(C=C, object_id=child_id, blob=b)

    # get uploaded child object JSON
    objects_results = _download_object(C=C, object_id=child_id)
    found = objects_results['found']
    if found:
        print('text:')
        print(objects_results)
        child_sumo_id = objects_results['_id']
    else:
        raise Exception(f'Object not found : {found}')

    # search for child, get one hit
    search_results = C.api.search('testdata_uniquetext:{}'.format(unique_text))
    hits = search_results.get('hits').get('hits')
    total = search_results.get('hits').get('total').get('value')
    assert total == 1
    assert len(hits) == 1

    # delete child


