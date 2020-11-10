"""Example code for communicating with Sumo"""
import sys

try:
    sys.path.index('../src')  # Or os.getcwd() for this directory
except ValueError:
    sys.path.append('../src')  # Or os.getcwd() for this directory

import pytest
import yaml

from time import sleep
from sumo.wrapper import CallSumoApi


class Connection:
    def __init__(self):
        self.api = CallSumoApi() 


def _upload_parent_object(C, json):
    response = C.api.save_top_level_json(json=json)
    if not 200 <= response.status_code < 202:
        raise Exception(f'code: {response.status_code}, text: {response.text}')
    return response


def _upload_blob(C, blob, url=None, object_id=None):
    response = C.api.update_blob(object_id=object_id, blob=blob, url=url)
    print("Blob save " + str(response.status_code), flush=True)
    if not 200 <= response.status_code < 202:
        raise Exception(f'blob upload to object_id {object_id} returned {response.text} {response.status_code}')    
    return response


def _get_blob_uri(C, object_id):
    response = C.api.get_blob_uri(object_id=object_id)
    print("Blob save " + str(response.status_code), flush=True)
    if not 200 <= response.status_code < 202:
        raise Exception(f'get blob uri for {object_id} returned {response.text} {response.status_code}')    
    return response
    

def _download_object(C, object_id):
    json = C.api.get_json(object_id=object_id)
    return json


def _upload_child_level_json(C, parent_id, json):
    response = C.api.save_child_level_json(parent_id=parent_id, json=json)
    if not 200 <= response.status_code < 202:
        raise Exception(f'Response: {response.status_code}, Text: {response.text}')
    return response


def _delete_object(C, object_id):
    response = C.api.delete_object(object_id=object_id)
    return response


class ValueKeeper:
    """Class for keeping/passing values between tests"""
    pass


""" TESTS """


def test_upload_search_delete_ensemble_child():
    """
        Testing the wrapper functionalities.

        We upload an ensemble object along with a child. After that, we search for
        those objects to make sure they are available to the user. We then delete
        them and repeat the search to check if they were properly removed from sumo.
    """
    C = Connection()
    B = b'123456789'

    # Upload Ensemble
    with open('testdata/fmu_ensemble.yaml', 'r') as stream:
        fmu_ensemble_metadata = yaml.safe_load(stream)

    response_ensemble = _upload_parent_object(C=C, json=fmu_ensemble_metadata)
    ensemble_id = response_ensemble.json().get('objectid')
    fmu_ensemble_id = fmu_ensemble_metadata.get('fmu_ensemble').get('fmu_ensemble_id')

    assert 200 <= response_ensemble.status_code <= 202
    assert isinstance(response_ensemble.json(), dict)

    # Upload Regular Surface
    with open('testdata/fmu_regularsurface.yaml', 'r') as stream:
        fmu_regularsurface_metadata = yaml.safe_load(stream)
        fmu_regularsurface_metadata['_tests'] = {'test1': 'test'}

    response_surface = _upload_child_level_json(C=C, parent_id=ensemble_id, json=fmu_regularsurface_metadata)
    regularsurface_id = response_surface.json().get('objectid')

    assert 200 <= response_surface.status_code <= 202
    assert isinstance(response_surface.json(), dict)
    
    # Upload BLOB
    blob_url = response_surface.json().get('blob_url')
    response_blob = _upload_blob(C=C, blob=B, url=blob_url)
    assert 200 <= response_blob.status_code <= 202

    sleep(2)

    # Search for ensemble
    query = f'fmu_ensemble.fmu_ensemble_id:{fmu_ensemble_id}'
    search_results = C.api.searchroot(query, select='source', buckets='source')
    hits = search_results.get('hits').get('hits')
    assert len(hits) == 1
    assert hits[0].get('_id') == ensemble_id

    # Search for child object
    search_results = C.api.search(query='_tests.test1:test')
    total = search_results.get('hits').get('total').get('value')
    assert total == 1

    get_result = _download_object(C, object_id=regularsurface_id)
    assert get_result["_id"] == regularsurface_id

    # Search for blob
    bin_obj = C.api.get_blob(object_id=regularsurface_id)
    assert bin_obj == B

    # Delete Ensemble
    result = _delete_object(C=C, object_id=ensemble_id)
    assert result == 'Accepted'

    sleep(3)

    # Search for ensemble
    query = f'fmu_ensemble.fmu_ensemble_id:{fmu_ensemble_id}'
    search_results = C.api.searchroot(query, select='source', buckets='source')

    hits = search_results.get('hits').get('hits')
    assert len(hits) == 0

    # Search for child object
    search_results = C.api.search(query='_tests.test1:test')
    total = search_results.get('hits').get('total').get('value')
    assert total == 0


def test_fail_on_wrong_metadata():
    """
        Upload a parent object with erroneous metadata, confirm failure
    """
    C = Connection()
    with pytest.raises(Exception):
        assert _upload_parent_object(C=C, json={"some field": "some value"})


def test_upload_regularsurface_as_parent():
    """ 
        Adding a regular surface as a parent object
    """
    C = Connection()
    
    with open('testdata/fmu_regularsurface.yaml', 'r') as stream:
        fmu_ensemble_metadata = yaml.safe_load(stream)

    fmu_ensemble_metadata['fmu_ensemble']['fmu_ensemble_id'] = '11100000-0000-0000-0000-000000000055'

    # upload must raise an exception
    with pytest.raises(Exception):
        assert _upload_parent_object(C=C, json=fmu_ensemble_metadata)


def test_upload_duplicate_ensemble():
    """
        Adding a duplicate ensemble, both tries must return same id.
    """
    C = Connection()

    with open('testdata/fmu_ensemble.yaml', 'r') as stream:
        fmu_ensemble_metadata1 = yaml.safe_load(stream)

    with open('testdata/fmu_ensemble.yaml', 'r') as stream:
        fmu_ensemble_metadata2 = yaml.safe_load(stream)

    # Adding fake equal ID
    fmu_ensemble_metadata1['fmu_ensemble']['fmu_ensemble_id'] = '00000000-0000-0000-0000-000000000055'
    fmu_ensemble_metadata2['fmu_ensemble']['fmu_ensemble_id'] = '00000000-0000-0000-0000-000000000055'

    # upload ensemble metadata, get object_id
    response1 = _upload_parent_object(C=C, json=fmu_ensemble_metadata1)
    ensemble_id1 = response1.json().get('objectid')
    assert 200 <= response1.status_code <= 202

    # upload duplicated ensemble metadata, get object_id
    response2 = _upload_parent_object(C=C, json=fmu_ensemble_metadata2)
    ensemble_id2 = response2.json().get('objectid')
    assert 200 <= response2.status_code <= 202
    
    assert ensemble_id1 == ensemble_id2

    get_result = _download_object(C, object_id=ensemble_id1)
    assert get_result["_id"] == ensemble_id1

    # Delete Ensemble
    result = _delete_object(C=C, object_id=ensemble_id1)
    assert result == 'Accepted'

    # Search for ensemble
    with pytest.raises(Exception):
        assert _download_object(C, object_id=ensemble_id1)
