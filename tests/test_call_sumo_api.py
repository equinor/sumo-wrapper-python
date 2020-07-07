"""Example code for communicating with Sumo"""
import sys
import json
sys.path.insert(0,'c:/appl/sumo-wrapper-python/src/')
import pytest
from sumo.wrapper import CallSumoApi
import yaml
from time import sleep

class Connection:
    def __init__(self):
        self.api = CallSumoApi()
        self.api.get_bear_token()        

def _upload_parent_object(C, json):
    response = C.api.save_top_level_json(json=json)
    if not 200 <= response.status_code < 202:
        raise Exception(f'code: {response.status_code}, text: {response.text}')
    return response

def _upload_blob(C, object_id, blob, url=None):
    response = C.api.save_blob(object_id=object_id, blob=blob, url=url)
    print("Blob save " + str(response.status_code), flush=True);
    if not 200 <= response.status_code < 202:
        raise Exception(f'blob upload to object_id {object_id} returned {response.text} {response.status_code}')    
    return response.text

def _get_blob_uri(C, objectid, url=None):
    response = C.api.get_blob_uri(object_id=object_id)
    print("Blob save " + str(response.status_code), flush=True);
    if not 200 <= response.status_code < 202:
        raise Exception(f'get blob uri for {object_id} returned {response.text} {response.status_code}')    
    return response.text
    

def _download_object(C, object_id):
    json = C.api.get_json(object_id=object_id)
    return json

def _upload_child_level_json(C, parent_id, json):
    response = C.api.save_child_level_json(object_id=parent_id, json=json)
    if not 200 <= response.status_code < 202:
        raise Exception(f'Response: {response.status_code}, Text: {response.text}')
    return response

def _delete_object(C, object_id):
    response = C.api.delete_object(object_id=object_id)
    return response


class ValueKeeper:
    """Class for keeping/passing values between tests"""
    pass

V = ValueKeeper()
C = Connection()
b = b'123456789'

##### TESTS #####

def test_fail_on_wrong_metadata():

    # upload a parent object with erroneous metadata, confirm failure
    json = {"some field": "some value"}
    response = C.api.save_top_level_json(json=json)
    assert response.status_code == 400

def test_upload_ensemble():
    #C = Connection()

    with open('testdata/fmu_ensemble.yaml', 'r') as stream:
        fmu_ensemble_metadata = yaml.safe_load(stream)
        # add a test attribute
        fmu_ensemble_metadata['_test'] = {'test1': 'test2'}

    #upload ensemble metadata, get object_id
    response = _upload_parent_object(C=C, json=fmu_ensemble_metadata)
    assert response.status_code == 200, response.status_code
    assert isinstance(response.json(), dict)
    V.ensemble_id = response.json().get('objectid')
    V.fmu_ensemble_id = fmu_ensemble_metadata.get('fmu_ensemble').get('fmu_ensemble_id')

    print('ensemble uploaded, ensemble ID: {}'.format(V.ensemble_id))
    print('FMU ensemble ID: {}'.format(V.fmu_ensemble_id))

    assert V.ensemble_id != V.fmu_ensemble_id

    # wait
    sleep(2)


def test_search_for_ensemble():
    """Search for the uploaded ensemble, confirm 1 hit"""


    print('search for fmu_ensemble_id: {}'.format(V.fmu_ensemble_id))
    query = f'fmu_ensemble.fmu_ensemble_id:{V.fmu_ensemble_id}'
    search_results = C.api.searchroot(query, select='source', buckets='source')

    hits = search_results.get('hits').get('hits')

    if len(hits) == 0:
        print(query)
        print(search_results)

    assert len(hits) == 1


def test_upload_regularsurface():

    with open('testdata/fmu_regularsurface.yaml', 'r') as stream:
        fmu_regularsurface_metadata1 = yaml.safe_load(stream)
        fmu_regularsurface_metadata1['_tests'] = {'test1': 'test'}

    with open('testdata/fmu_regularsurface.yaml', 'r') as stream:
        fmu_regularsurface_metadata2 = yaml.safe_load(stream)
        fmu_regularsurface_metadata2['_tests'] = {'test2': 'test'}

        # manipulate local path to get different ID
        fmu_regularsurface_metadata2['data']['relative_file_path'] += '_2'

    assert fmu_regularsurface_metadata1 != fmu_regularsurface_metadata2

    #print('parent_id: {}'.format(ensemble_id))

    # upload regularsurface child object, get child_id
    response = _upload_child_level_json(C=C, parent_id=V.ensemble_id, json=fmu_regularsurface_metadata1)
    V.regularsurface_id1 = response.json().get('objectid')
    results = _upload_blob(C=C, object_id=V.regularsurface_id1, blob=b)
    assert results == '"Created"'

    response = _upload_child_level_json(C=C, parent_id=V.ensemble_id, json=fmu_regularsurface_metadata2)
    V.regularsurface_id2 = response.json().get('objectid')
    results = _upload_blob(C=C, object_id=V.regularsurface_id2, blob=b)
    assert results == '"Created"'

    # confirm that the two childs are different objects on Sumo
    print(fmu_regularsurface_metadata1.get('data').get('relative_file_path'))
    print(fmu_regularsurface_metadata2.get('data').get('relative_file_path'))
    assert V.regularsurface_id1 != V.regularsurface_id2


def test_search_for_regularsurface():

    # search for regularsurface, get one hit
    search_results = C.api.search(query='_tests.test1:test')
    print(search_results)
    hits = search_results.get('hits').get('hits')
    total = search_results.get('hits').get('total').get('value')

    # confirm that search gives 1 hit only
    assert total == 1
    assert len(hits) == 1

    # confirm that the one hit is the same as was previously uploaded
    _id = hits[0].get('_id')
    assert V.regularsurface_id1 == _id

def test_delete_regularsurface():

    # delete regularsurface
    result = _delete_object(C=C, object_id=V.regularsurface_id1)
    assert result == 'Accepted'

    # wait
    sleep(2)


def test_search_for_nonexisting_regularsurface():


    # search for regularsurface, get zero hits
    search_results = C.api.search(query='_tests.test1:test')
    print(search_results)
    hits = search_results.get('hits').get('hits')
    total = search_results.get('hits').get('total').get('value')

    assert total == 0
    assert len(hits) == 0


def test_delete_ensemble():

    # delete parent
    result = _delete_object(C=C, object_id=V.ensemble_id)
    assert result == 'Accepted'

    # search for child1, get zero hits
    search_results = C.api.search('_tests:test1')
    hits = search_results.get('hits').get('hits')
    total = search_results.get('hits').get('total').get('value')
    assert total == 0
    assert len(hits) == 0

# download
#    # get child1 JSON
#    objects_results = _download_object(C=C, object_id=V.regularsurface_id)
#    found = objects_results['found']
#    if found:
#        print('text:')
#        print(objects_results)
#    else:
#        raise Exception(f'Object not found : {found}')#