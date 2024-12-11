"""Example code for communicating with Sumo"""

import os
import sys
import uuid
from time import sleep

import pytest
import yaml

sys.path.append(os.path.abspath(os.path.join("src")))

from sumo.wrapper import SumoClient  # noqa: E402


def _upload_parent_object(conn, json):
    response = conn.post("/objects", json=json)

    if not 200 <= response.status_code < 202:
        raise Exception(f"code: {response.status_code}, text: {response.text}")
    return response


def _upload_blob(conn, blob, url=None, object_id=None):
    response = conn.blob_client.upload_blob(blob=blob, url=url)

    print("Blob save " + str(response.status_code), flush=True)
    if not 200 <= response.status_code < 202:
        raise Exception(
            f"blob upload to object_id {object_id}"
            f" returned {response.text} {response.status_code}"
        )
    return response


def _get_blob_uri(conn, object_id):
    response = conn.get(f"/objects('{object_id}')/blob/authuri")

    print("Blob save " + str(response.status_code), flush=True)
    if not 200 <= response.status_code < 202:
        raise Exception(
            f"get blob uri for {object_id}"
            f" returned {response.text} {response.status_code}"
        )
    return response


def _download_object(conn, object_id):
    json = conn.get(f"/objects('{object_id}')").json()

    return json


def _upload_child_level_json(conn, parent_id, json):
    response = conn.post(f"/objects('{parent_id}')", json=json)

    if not 200 <= response.status_code < 202:
        raise Exception(
            f"Response: {response.status_code}, Text: {response.text}"
        )
    return response


def _delete_object(conn, object_id):
    response = conn.delete(f"/objects('{object_id}')").json()

    return response


class ValueKeeper:
    """Class for keeping/passing values between tests"""

    pass


""" TESTS """


def test_upload_search_delete_ensemble_child(token):
    """
    Testing the wrapper functionalities.

    We upload an ensemble object along with a child. After that, we search for
    those objects to make sure they are available to the user. We then delete
    them and repeat the search to check if they were properly removed from sumo.
    """
    sumo_client = SumoClient(env="dev", token=token)
    blob = b"123456789"

    # Upload Ensemble
    with open("tests/testdata/case.yml", "r") as stream:
        fmu_case_metadata = yaml.safe_load(stream)

    case_uuid = str(uuid.uuid4())
    fmu_case_metadata["fmu"]["case"]["uuid"] = case_uuid

    response_case = _upload_parent_object(
        conn=sumo_client, json=fmu_case_metadata
    )

    assert 200 <= response_case.status_code <= 202
    assert isinstance(response_case.json(), dict)

    case_id = response_case.json().get("objectid")
    assert case_id == case_uuid

    sleep(5)

    # Upload Regular Surface
    with open("tests/testdata/surface.yml", "r") as stream:
        fmu_surface_metadata = yaml.safe_load(stream)

    fmu_surface_metadata["fmu"]["case"]["uuid"] = case_uuid

    response_surface = _upload_child_level_json(
        conn=sumo_client, parent_id=case_id, json=fmu_surface_metadata
    )

    assert 200 <= response_surface.status_code <= 202
    assert isinstance(response_surface.json(), dict)

    surface_id = response_surface.json().get("objectid")
    blob_url = response_surface.json().get("blob_url")

    # Upload BLOB
    response_blob = _upload_blob(
        conn=sumo_client, blob=blob, url=blob_url, object_id=surface_id
    )
    assert 200 <= response_blob.status_code <= 202

    sleep(4)

    # Search for ensemble
    query = f"fmu.case.uuid:{case_uuid}"

    search_results = sumo_client.get(
        "/searchroot", params={"$query": query, "$select": ["_source"]}
    ).json()

    hits = search_results.get("hits").get("hits")
    assert len(hits) == 1
    assert hits[0].get("_id") == case_id

    # Search for child object
    search_results = sumo_client.get(
        "/search", {"$query": query, "$select": ["_source"]}
    ).json()

    total = search_results.get("hits").get("total").get("value")
    assert total == 2

    get_result = _download_object(sumo_client, object_id=surface_id)
    assert get_result["_id"] == surface_id

    # Search for blob
    bin_obj = sumo_client.get(f"/objects('{surface_id}')/blob").content
    assert bin_obj == blob

    # Delete Ensemble
    result = _delete_object(conn=sumo_client, object_id=case_id)
    assert result == "Accepted"

    sleep(40)

    # Search for ensemble
    search_results = sumo_client.get(
        "/searchroot", {"$query": query, "$select": ["_source"]}
    ).json()

    hits = search_results.get("hits").get("hits")

    assert len(hits) == 0

    # Search for child object
    search_results = sumo_client.get(
        "/search", {"$query": query, "$select": ["_source"]}
    ).json()
    total = search_results.get("hits").get("total").get("value")
    assert total == 0


def test_fail_on_wrong_metadata(token):
    """
    Upload a parent object with erroneous metadata, confirm failure
    """
    conn = SumoClient(env="dev", token=token)
    with pytest.raises(Exception):
        assert _upload_parent_object(
            conn=conn, json={"some field": "some value"}
        )


def test_upload_duplicate_ensemble(token):
    """
    Adding a duplicate ensemble, both tries must return same id.
    """
    conn = SumoClient(env="dev", token=token)

    with open("tests/testdata/case.yml", "r") as stream:
        fmu_metadata1 = yaml.safe_load(stream)

    with open("tests/testdata/case.yml", "r") as stream:
        fmu_metadata2 = yaml.safe_load(stream)

    case_uuid = str(uuid.uuid4())
    fmu_metadata1["fmu"]["case"]["uuid"] = case_uuid
    fmu_metadata2["fmu"]["case"]["uuid"] = case_uuid

    # upload case metadata, get object_id
    response1 = _upload_parent_object(conn=conn, json=fmu_metadata1)
    assert 200 <= response1.status_code <= 202

    # upload duplicated case metadata, get object_id
    response2 = _upload_parent_object(conn=conn, json=fmu_metadata2)
    assert 200 <= response2.status_code <= 202

    case_id1 = response1.json().get("objectid")
    case_id2 = response2.json().get("objectid")
    assert case_id1 == case_id2

    get_result = _download_object(conn, object_id=case_id1)
    assert get_result["_id"] == case_id1

    # Delete Ensemble
    sleep(5)
    result = _delete_object(conn=conn, object_id=case_id1)
    assert result == "Accepted"

    # Ugly: sumo-core has a cache for case objects, which has a
    # time-to-live of 60 seconds. If there are multiple replicas
    # running, we might get the situation where we have just deleted
    # the case via one replica, then ask for the object from another
    # replica which still has it ins cache. Thus, the magic value 61,
    # below.
    sleep(61)

    # Search for ensemble
    with pytest.raises(Exception):
        assert _download_object(conn, object_id=case_id2)
