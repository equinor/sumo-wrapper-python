"""Example code for communicating with Sumo"""
import sys

try:
    sys.path.index("../src")  # Or os.getcwd() for this directory
except ValueError:
    sys.path.append("../src")  # Or os.getcwd() for this directory

import pytest
import yaml

from time import sleep
from sumo.wrapper import CallSumoApi


class Connection:
    def __init__(self):
        self.api = CallSumoApi(env="dev")


def _upload_parent_object(C, json):
    response = C.api.save_top_level_json(json=json)
    if not 200 <= response.status_code < 202:
        raise Exception(f"code: {response.status_code}, text: {response.text}")
    return response


def _upload_blob(C, blob, url=None, object_id=None):
    response = C.api.save_blob(object_id=object_id, blob=blob, url=url)
    print("Blob save " + str(response.status_code), flush=True)
    if not 200 <= response.status_code < 202:
        raise Exception(
            f"blob upload to object_id {object_id} returned {response.text} {response.status_code}"
        )
    return response


def _get_blob_uri(C, object_id):
    response = C.api.get_blob_uri(object_id=object_id)
    print("Blob save " + str(response.status_code), flush=True)
    if not 200 <= response.status_code < 202:
        raise Exception(
            f"get blob uri for {object_id} returned {response.text} {response.status_code}"
        )
    return response


def _download_object(C, object_id):
    json = C.api.get_json(object_id=object_id)
    return json


def _upload_child_level_json(C, parent_id, json):
    response = C.api.save_child_level_json(parent_id=parent_id, json=json)
    if not 200 <= response.status_code < 202:
        raise Exception(f"Response: {response.status_code}, Text: {response.text}")
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
    B = b"123456789"

    # Upload Ensemble
    with open("tests/testdata/case.yml", "r") as stream:
        fmu_case_metadata = yaml.safe_load(stream)

    response_case = _upload_parent_object(C=C, json=fmu_case_metadata)

    assert 200 <= response_case.status_code <= 202
    assert isinstance(response_case.json(), dict)

    case_id = response_case.json().get("objectid")
    fmu_case_id = fmu_case_metadata.get("fmu").get("case").get("uuid")

    # Upload Regular Surface
    with open("tests/testdata/surface.yml", "r") as stream:
        fmu_surface_metadata = yaml.safe_load(stream)

    fmu_surface_id = fmu_surface_metadata.get("fmu").get("realization").get("id")
    response_surface = _upload_child_level_json(
        C=C, parent_id=case_id, json=fmu_surface_metadata
    )

    assert 200 <= response_surface.status_code <= 202
    assert isinstance(response_surface.json(), dict)

    surface_id = response_surface.json().get("objectid")

    # Upload BLOB
    url = response_surface.json().get("blob_url")
    response_blob = _upload_blob(C=C, blob=B, object_id=surface_id, url=url)
    assert 200 <= response_blob.status_code <= 202

    sleep(4)

    # Search for ensemble
    query = f"{fmu_case_id}"
    search_results = C.api.searchroot(query, select="_source")

    hits = search_results.get("hits").get("hits")
    assert len(hits) == 1
    assert hits[0].get("_id") == case_id

    # Search for child object

    search_results = C.api.search(query, select="_source")

    total = search_results.get("hits").get("total").get("value")
    assert total == 2

    get_result = _download_object(C, object_id=surface_id)
    assert get_result["_id"] == surface_id

    # Search for blob
    bin_obj = C.api.get_blob(object_id=surface_id)
    assert bin_obj == B

    # Delete Ensemble
    result = _delete_object(C=C, object_id=case_id)
    assert result == "Accepted"

    sleep(4)

    # Search for ensemble
    search_results = C.api.searchroot(query, select="_source")

    hits = search_results.get("hits").get("hits")

    assert len(hits) == 0

    # Search for child object
    search_results = C.api.search(query, select="source")
    total = search_results.get("hits").get("total").get("value")
    assert total == 0


def test_direct_blob_store_upload():
    """
    Testing the wrapper functionalities.

    We upload an ensemble object along with a child. After that, we search for
    those objects to make sure they are available to the user. We then delete
    them and repeat the search to check if they were properly removed from sumo.
    """
    C = Connection()
    B = b"123456789"

    # Upload Ensemble
    with open("tests/testdata/case.yml", "r") as stream:
        fmu_case_metadata = yaml.safe_load(stream)

    response_case = _upload_parent_object(C=C, json=fmu_case_metadata)

    assert 200 <= response_case.status_code <= 202
    assert isinstance(response_case.json(), dict)

    case_id = response_case.json().get("objectid")
    fmu_case_id = fmu_case_metadata.get("fmu").get("case").get("uuid")

    # Upload Regular Surface
    with open("tests/testdata/surface.yml", "r") as stream:
        fmu_surface_metadata = yaml.safe_load(stream)

    fmu_surface_id = fmu_surface_metadata.get("fmu").get("realization").get("id")
    response_surface = _upload_child_level_json(
        C=C, parent_id=case_id, json=fmu_surface_metadata
    )

    assert 200 <= response_surface.status_code <= 202
    assert isinstance(response_surface.json(), dict)

    surface_id = response_surface.json().get("objectid")

    # Upload BLOB
    blob_url = response_surface.json().get("blob_url")
    response_blob = _upload_blob(C=C, blob=B, url=blob_url)
    assert 200 <= response_blob.status_code <= 202

    sleep(4)

    # Search for ensemble
    query = f"{fmu_case_id}"
    search_results = C.api.searchroot(query, select="_source")

    hits = search_results.get("hits").get("hits")
    assert len(hits) == 1
    assert hits[0].get("_id") == case_id

    # Search for child object

    search_results = C.api.search(query, select="_source")

    total = search_results.get("hits").get("total").get("value")
    assert total == 2

    get_result = _download_object(C, object_id=surface_id)
    assert get_result["_id"] == surface_id

    # Search for blob
    bin_obj = C.api.get_blob(object_id=surface_id)
    assert bin_obj == B

    # Delete Ensemble
    result = _delete_object(C=C, object_id=case_id)
    assert result == "Accepted"

    sleep(4)

    # Search for ensemble
    search_results = C.api.searchroot(query, select="_source")

    hits = search_results.get("hits").get("hits")

    assert len(hits) == 0

    # Search for child object
    search_results = C.api.search(query, select="source")
    total = search_results.get("hits").get("total").get("value")
    assert total == 0


def test_direct_blob_store_upload_single_operation():
    """
    Testing the wrapper functionalities.

    We upload an ensemble object along with a child. After that, we search for
    those objects to make sure they are available to the user. We then delete
    them and repeat the search to check if they were properly removed from sumo.
    """

    C = Connection()
    B = b"123456789"

    # Upload Ensemble
    with open("tests/testdata/case.yml", "r") as stream:
        fmu_case_metadata = yaml.safe_load(stream)

    response_case = _upload_parent_object(C=C, json=fmu_case_metadata)

    assert 200 <= response_case.status_code <= 202
    assert isinstance(response_case.json(), dict)

    case_id = response_case.json().get("objectid")
    fmu_case_id = fmu_case_metadata.get("fmu").get("case").get("uuid")

    # Upload Regular Surface
    with open("tests/testdata/surface.yml", "r") as stream:
        fmu_surface_metadata = yaml.safe_load(stream)

    fmu_surface_id = fmu_surface_metadata.get("fmu").get("realization").get("id")

    response_surface = C.api.save_blob_and_json(case_id, fmu_surface_metadata, B)

    assert 200 <= response_surface.status_code <= 202
    assert isinstance(response_surface.json(), dict)

    surface_id = response_surface.json().get("objectid")

    sleep(4)

    # Search for ensemble
    query = f"{fmu_case_id}"
    search_results = C.api.searchroot(query, select="_source")

    hits = search_results.get("hits").get("hits")
    assert len(hits) == 1
    assert hits[0].get("_id") == case_id

    # Search for child object

    search_results = C.api.search(query, select="_source")

    total = search_results.get("hits").get("total").get("value")
    assert total == 2

    get_result = _download_object(C, object_id=surface_id)
    assert get_result["_id"] == surface_id

    # Search for blob
    bin_obj = C.api.get_blob(object_id=surface_id)
    assert bin_obj == B

    # Delete Ensemble
    result = _delete_object(C=C, object_id=case_id)
    assert result == "Accepted"

    sleep(4)

    # Search for ensemble
    search_results = C.api.searchroot(query, select="_source")

    hits = search_results.get("hits").get("hits")

    assert len(hits) == 0

    # Search for child object
    search_results = C.api.search(query, select="source")
    total = search_results.get("hits").get("total").get("value")
    assert total == 0


def test_search_after():
    """
    Testing the wrapper functionalities.

    We upload an ensemble object along with a child. After that, we search for
    those objects to make sure they are available to the user. We then delete
    them and repeat the search to check if they were properly removed from sumo.
    """

    C = Connection()
    B = b"123456789"

    # Upload Ensemble
    with open("tests/testdata/case.yml", "r") as stream:
        fmu_case_metadata = yaml.safe_load(stream)

    response_case = _upload_parent_object(C=C, json=fmu_case_metadata)

    assert 200 <= response_case.status_code <= 202
    assert isinstance(response_case.json(), dict)

    case_id = response_case.json().get("objectid")
    fmu_case_id = fmu_case_metadata.get("fmu").get("case").get("uuid")

    # Upload Regular Surface
    with open("tests/testdata/surface.yml", "r") as stream:
        fmu_surface_metadata = yaml.safe_load(stream)

    fmu_surface_id = fmu_surface_metadata.get("fmu").get("realization").get("id")

    response_surface = C.api.save_blob_and_json(case_id, fmu_surface_metadata, B)

    assert 200 <= response_surface.status_code <= 202
    assert isinstance(response_surface.json(), dict)

    surface_id = response_surface.json().get("objectid")

    sleep(2)

    # Search for child object

    query = f"{fmu_case_id}"
    search_results = C.api.search(query, search_size="1", select="_source")

    num_results = len(search_results.get("hits").get("hits"))
    search_after = search_results.get("hits").get("hits")[num_results - 1].get("sort")

    assert num_results == 1

    search_results = C.api.search(query, search_after=search_after, select="_source")
    num_results = len(search_results.get("hits").get("hits"))

    # assert num_results == 1

    # Delete Ensemble
    result = _delete_object(C=C, object_id=case_id)
    assert result == "Accepted"

    sleep(3)

    # Search for ensemble
    search_results = C.api.searchroot(query, select="_source")

    hits = search_results.get("hits").get("hits")

    assert len(hits) == 0

    # Search for child object
    search_results = C.api.search(query, select="source")
    total = search_results.get("hits").get("total").get("value")
    assert total == 0


def test_fail_on_wrong_metadata():
    """
    Upload a parent object with erroneous metadata, confirm failure
    """
    C = Connection()
    with pytest.raises(Exception):
        assert _upload_parent_object(C=C, json={"some field": "some value"})


def test_upload_duplicate_ensemble():
    """
    Adding a duplicate ensemble, both tries must return same id.
    """
    C = Connection()

    with open("tests/testdata/case.yml", "r") as stream:
        fmu_metadata1 = yaml.safe_load(stream)

    with open("tests/testdata/case.yml", "r") as stream:
        fmu_metadata2 = yaml.safe_load(stream)

    # upload case metadata, get object_id
    response1 = _upload_parent_object(C=C, json=fmu_metadata1)
    assert 200 <= response1.status_code <= 202

    # upload duplicated case metadata, get object_id
    response2 = _upload_parent_object(C=C, json=fmu_metadata2)
    assert 200 <= response2.status_code <= 202

    case_id1 = response1.json().get("objectid")
    case_id2 = response2.json().get("objectid")
    assert case_id1 == case_id2

    get_result = _download_object(C, object_id=case_id1)
    assert get_result["_id"] == case_id1

    # Delete Ensemble
    result = _delete_object(C=C, object_id=case_id1)
    assert result == "Accepted"

    # Search for ensemble
    with pytest.raises(Exception):
        assert _download_object(C, object_id=case_id2)
