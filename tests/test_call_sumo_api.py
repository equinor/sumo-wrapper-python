"""Example code for communicating with Sumo"""
import sys
import json
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

def _upload_blob(C, blob, url=None, object_id=None):
    response = C.api.save_blob(object_id=object_id, blob=blob, url=url)
    print("Blob save " + str(response.status_code), flush=True);
    if not 200 <= response.status_code < 202:
        raise Exception(f'blob upload to object_id {object_id} returned {response.text} {response.status_code}')    
    return response

def _get_blob_uri(C, objectid, url=None):
    response = C.api.get_blob_uri(object_id=object_id)
    print("Blob save " + str(response.status_code), flush=True);
    if not 200 <= response.status_code < 202:
        raise Exception(f'get blob uri for {object_id} returned {response.text} {response.status_code}')    
    return response
    

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
    assert 200 <= response.status_code <= 202, response.status_code
    assert isinstance(response.json(), dict)
    V.ensemble_id = response.json().get('objectid')
    V.fmu_ensemble_id = fmu_ensemble_metadata.get('fmu_ensemble').get('fmu_ensemble_id')

    print('ensemble uploaded, ensemble ID: {}'.format(V.ensemble_id))
    print('FMU ensemble ID: {}'.format(V.fmu_ensemble_id))

    assert V.ensemble_id != V.fmu_ensemble_id

    # wait
    sleep(2)

# Adding a duplicate ensemble, both tries must return same id.
def test_upload_duplicate_ensemble():
    with open('testdata/fmu_ensemble.yaml', 'r') as stream:
        fmu_ensemble_metadata1 = yaml.safe_load(stream)

    with open('testdata/fmu_ensemble.yaml', 'r') as stream:
        fmu_ensemble_metadata2 = yaml.safe_load(stream)

    # Adding fake equal ID
    fmu_ensemble_metadata1['fmu_ensemble']['fmu_ensemble_id'] = '00000000-0000-0000-0000-000000000055'
    fmu_ensemble_metadata2['fmu_ensemble']['fmu_ensemble_id'] = '00000000-0000-0000-0000-000000000055'

    #upload ensemble metadata, get object_id
    response1 = _upload_parent_object(C=C, json=fmu_ensemble_metadata1)
    
    V.ensemble_id1 = response1.json().get('objectid')
    V.fmu_ensemble_id1 = fmu_ensemble_metadata1.get('fmu_ensemble').get('fmu_ensemble_id')

    assert 200 <= response1.status_code <= 202, response1.status_code
    assert isinstance(response1.json(), dict)

    #upload duplicated ensemble metadata, get object_id
    response2 = _upload_parent_object(C=C, json=fmu_ensemble_metadata2)

    V.ensemble_id2 = response1.json().get('objectid')
    V.fmu_ensemble_id2 = fmu_ensemble_metadata2.get('fmu_ensemble').get('fmu_ensemble_id')

    assert 200 <= response2.status_code <= 202, response2.status_code
    assert isinstance(response2.json(), dict)
    
    assert V.ensemble_id1 == V.ensemble_id2
    assert V.ensemble_id != V.ensemble_id1

# Adding a regular surface as a parent object
def test_upload_regularsurface_as_parent():
    with open('testdata/fmu_regularsurface.yaml', 'r') as stream:
        fmu_ensemble_metadata = yaml.safe_load(stream)

    fmu_ensemble_metadata['fmu_ensemble']['fmu_ensemble_id'] = '11100000-0000-0000-0000-000000000055'

    # upload must raise an exception
    try:
        response = _upload_parent_object(C=C, json=fmu_ensemble_metadata)
    except:
        assert True
    else:
        assert False

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

    # upload regularsurface child object, get child_id
    response_json = _upload_child_level_json(C=C, parent_id=V.ensemble_id, json=fmu_regularsurface_metadata1)
    V.regularsurface_id1 = response_json.json().get('objectid')
    url = response_json.json().get('blob_url')
    response_blob = _upload_blob(C=C, blob=b, url=url)
    assert response_blob.status_code == 201

    response_json = _upload_child_level_json(C=C, parent_id=V.ensemble_id, json=fmu_regularsurface_metadata2)
    V.regularsurface_id2 = response_json.json().get('objectid')
    url = response_json.json().get('blob_url')
    response_blob = _upload_blob(C=C, blob=b, url=url)
    assert response_blob.status_code == 201

    # confirm that the two childs are different objects on Sumo
    print(fmu_regularsurface_metadata1.get('data').get('relative_file_path'))
    print(fmu_regularsurface_metadata2.get('data').get('relative_file_path'))
    assert V.regularsurface_id1 != V.regularsurface_id2

    sleep(5)

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
    sleep(5)

def test_search_for_nonexisting_regularsurface():
    """Search for regularsurface, get zero hits"""
    search_results = C.api.search(query='_tests.test1:test')
    print(search_results)
    hits = search_results.get('hits').get('hits')
    total = search_results.get('hits').get('total').get('value')

    assert total == 0
    assert len(hits) == 0

def test_upload_polygon():
    with open('testdata/fmu_polygons.yaml', 'r') as stream:
        fmu_polygon_metadata = yaml.safe_load(stream)
        fmu_polygon_metadata['_tests'] = {'test1': 'test-pol'}

    # upload polygon child object, get child_id
    response_json = _upload_child_level_json(C=C, parent_id=V.ensemble_id, json=fmu_polygon_metadata)
    
    assert response_json.status_code <= 202

    V.polygon_id = response_json.json().get('objectid')
    url = response_json.json().get('blob_url')
    response_blob = _upload_blob(C=C, blob=b, url=url)
    
    assert response_blob.status_code == 201

    sleep(2)

def test_upload_duplicate_polygon_different_parents():
    with open('testdata/fmu_polygons.yaml', 'r') as stream:
        fmu_polygon_metadata = yaml.safe_load(stream)
        fmu_polygon_metadata['_tests'] = {'test3': 'test-pol3'}

    # upload polygon child object, get child_id
    try:
        response_json = _upload_child_level_json(C=C, parent_id=V.ensemble_id1, json=fmu_polygon_metadata)
    except:
        assert True
    else:
        assert False

    sleep(2)


# Check if dublicate children are treated as the same object.
def test_upload_duplicate_polygon():
    with open('testdata/fmu_polygons.yaml', 'r') as stream:
        fmu_polygon_metadata1 = yaml.safe_load(stream)
        fmu_polygon_metadata1['_tests'] = {'test1': 'test-pol1'}

    with open('testdata/fmu_polygons.yaml', 'r') as stream:
        fmu_polygon_metadata2 = yaml.safe_load(stream)
        fmu_polygon_metadata2['_tests'] = {'test2': 'test-pol2'}

    # upload regularsurface child object, get child_id
    response_json = _upload_child_level_json(C=C, parent_id=V.ensemble_id, json=fmu_polygon_metadata1)
    V.polygon_id1 = response_json.json().get('objectid')
    url = response_json.json().get('blob_url')
    response_blob = _upload_blob(C=C, blob=b, url=url)
    assert response_blob.status_code == 201

    response_json = _upload_child_level_json(C=C, parent_id=V.ensemble_id, json=fmu_polygon_metadata2)
    V.polygon_id2 = response_json.json().get('objectid')
    url = response_json.json().get('blob_url')
    response_blob = _upload_blob(C=C, blob=b, url=url)
    assert response_blob.status_code == 201

    # confirm that the two childs are different objects on Sumo
    print(fmu_polygon_metadata1.get('data').get('relative_file_path'))
    print(fmu_polygon_metadata2.get('data').get('relative_file_path'))
    assert V.polygon_id1 == V.polygon_id2

    sleep(2)

def test_upload_ensemble_as_child():
    with open('testdata/fmu_ensemble.yaml', 'r') as stream:
        fmu_ensemble_metadata = yaml.safe_load(stream)
        fmu_ensemble_metadata['_tests'] = {'test1': 'test-ensemble-child'}
        fmu_ensemble_metadata['fmu_ensemble']['fmu_ensemble_id'] = '00000000-2222-0000-0000-000000000055'

    try:
        response_json = _upload_child_level_json(C=C, parent_id=V.ensemble_id, json=fmu_ensemble_metadata)
    except:
        assert True
    else:
        assert False
    
    sleep(2)

def test_delete_ensemble():

    result = _delete_object(C=C, object_id=V.ensemble_id)
    print(result, V.fmu_ensemble_id)

    sleep(3)

    # search for child1, get zero hits
    search_results = C.api.search('_test.test1:test2')
    hits = search_results.get('hits').get('hits')
    total = search_results.get('hits').get('total').get('value')
    assert total == 0
    assert len(hits) == 0

    print('search for fmu_ensemble_id: {}'.format(V.fmu_ensemble_id))
    query = f'fmu_ensemble.fmu_ensemble_id:{V.fmu_ensemble_id}'
    search_results = C.api.searchroot(query, select='source', buckets='source')
    hits = search_results.get('hits').get('hits')

    if len(hits) == 0:
        print(query)
        print(search_results)

    assert len(hits) == 0

def test_search_for_regularsurface_after_ensemble_removal():
    search_results = C.api.search(query='_tests.test2:test')
    print(search_results)
    hits = search_results.get('hits').get('hits')
    total = search_results.get('hits').get('total').get('value')

    # confirm that search gives no hit
    assert total == 0
    assert len(hits) == 0

def test_upload_ensemble_after_removal():
    with open('testdata/fmu_ensemble.yaml', 'r') as stream:
        fmu_ensemble_metadata = yaml.safe_load(stream)
        fmu_ensemble_metadata['_test'] = {'test1': 'test2'}

    response = _upload_parent_object(C=C, json=fmu_ensemble_metadata)
    assert 200 <= response.status_code <= 202, response.status_code
    assert isinstance(response.json(), dict)
    V.ensemble_id = response.json().get('objectid')
    V.fmu_ensemble_id = fmu_ensemble_metadata.get('fmu_ensemble').get('fmu_ensemble_id')

    print('ensemble uploaded, ensemble ID: {}'.format(V.ensemble_id))
    print('FMU ensemble ID: {}'.format(V.fmu_ensemble_id))

    assert V.ensemble_id != V.fmu_ensemble_id

    # wait
    sleep(2)

def test_search_for_ensemble_after_reinserting():
    print('search for fmu_ensemble_id: {}'.format(V.fmu_ensemble_id))
    query = f'fmu_ensemble.fmu_ensemble_id:{V.fmu_ensemble_id}'
    search_results = C.api.searchroot(query, select='source', buckets='source')

    hits = search_results.get('hits').get('hits')

    if len(hits) == 0:
        print(query)
        print(search_results)

    assert len(hits) == 1

# download
#    # get child1 JSON
#    objects_results = _download_object(C=C, object_id=V.regularsurface_id)
#    found = objects_results['found']
#    if found:
#        print('text:')
#        print(objects_results)
#    else:
#        raise Exception(f'Object not found : {found}')#

# test_upload_ensemble()
# test_search_for_ensemble()