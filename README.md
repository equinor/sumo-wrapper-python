# sumo-wrapper-python

Python wrappers for Sumo APIs

## Install:

    pip install sumo-wrapper-python

For internal Equinor users, this package is available through the Komodo
distribution.

> **:warning:** `CallSumoApi` is deprecated.

# Table of contents

- [sumo-wrapper-python](#sumo-wrapper-python)
  - [Install:](#install)
- [Table of contents](#table-of-contents)
- [SumoClient](#sumoclient)
    - [Initialization](#initialization)
    - [Parameters](#parameters)
          - [`token` logic](#token-logic)
  - [Methods](#methods)
    - [get(path, \*\*params)](#getpath-params)
    - [post(path, json, blob)](#postpath-json-blob)
    - [put(path, json, blob)](#putpath-json-blob)
    - [delete(path)](#deletepath)
  - [Async methods](#async-methods)
- [CallSumoApi (deprecated)](#callsumoapi-deprecated)
    - [Initialization](#initialization-1)
    - [Parameters](#parameters-1)
  - [Examples](#examples)
    - [search()](#search)
      - [Parameters](#parameters-2)
      - [Usage](#usage)
    - [searchroot()](#searchroot)
      - [Parameters](#parameters-3)
      - [Usage](#usage-1)

# SumoClient

A thin wrapper class for the Sumo API.

### Initialization

```python
from sumo.wrapper import SumoClient

sumo = SumoClient(env="dev")
```

### Parameters

```python
class SumoClient:
    def __init__(
        self,
        env:str,
        token:str=None,
        interactive:bool=False,
        verbosity:str="CRITICAL"
    ):
```

- `env`: sumo environment
- `token`: bearer token or refresh token
- `interactive`: use interactive flow when authenticating
- `verbosity`: "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"

###### `token` logic

If an access token is provided in the `token` parameter, it will be used as long
as it's valid. An error will be raised when it expires.

If we are unable to decode the provided `token` as a JWT, we treat it as a
refresh token and attempt to use it to retrieve an access token.

If no `token` is provided, an authentication code flow/interactive flow is
triggered to retrieve a token.

## Methods

`SumoClient` has one method for each HTTP-method that is used in the sumo-core
API. See examples of how to use these methods below.

All methods accepts a path argument. Path parameters can be interpolated into
the path string. Example:

```python
object_id = "1234"

# GET/objects('{obejctid}')
sumo.get(f"/objects('{object_id}')")
```

### get(path, \*\*params)

Performs a GET-request to sumo-core. Accepts query parameters as keyword
arguments.

```python
# Retrieve userdata
user_data = sumo.get("/userdata")

# Search for objects
results = sumo.get("/search",
    query="class:surface",
    size:3,
    select=["_id"]
)

# Get object by id
object_id = "159405ba-0046-b321-55ce-542f383ba5c7"

obj = sumo.get(f"/objects('{object_id}')")
```

### post(path, json, blob)

Performs a POST-request to sumo-core. Accepts json and blob, but not both at the
same time.

```python
# Upload new parent object
parent_object = sumo.post("/objects", json=parent_meta_data)

# Upload child object
parent_id = parent_object["_id"]

child_object = sumo.post(f"/objects('{parent_id}')", json=child_meta_data)
```

### put(path, json, blob)

Performs a PUT-request to sumo-core. Accepts json and blob, but not both at the
same time.

```python
# Upload blob to child object
child_id = child_object["_id"]

sumo.put(f"/objects('{child_id}')/blob", blob=blob)
```

### delete(path)

Performs a DELETE-request to sumo-core.

```python
# Delete blob
sumo.delete(f"/objects('{child_id}')/blob")

# Delete child object
sumo.delete(f"/objects('{child_id}')")

# Delete parent object
sumo.delete(f"/objects('{parent_id}')")
```

## Async methods

`SumoClient` also has *async* alternatives `get_async`, `post_async`, `put_async` and `delete_async`.
These accept the same parameters as their synchronous counterparts, but have to be *awaited*.

```python
# Retrieve userdata
user_data = await sumo.get_async("/userdata")
```

# CallSumoApi (deprecated)

Predefined methods for various sumo operations. I.e uploading, searching for and
deleting metadata and blobs.

### Initialization

```python
from sumo.wrapper import CallSumoApi

sumo = CallSumoApi()
```

### Parameters

```python
class CallSumoApi:
    def __init__(
        self,
        env="dev",
        resource_id=None,
        client_id=None,
        outside_token=False,
        writeback=False,
    ):
```

## Examples

All `CallSumoApi` methods accept a `bearer` argument which lets the user use an
existing access token instead of generating a new one.

### search()

Search all objects in sumo.

#### Parameters

```python
def search(
    self,
    query,
    select=None,
    buckets=None,
    search_from=0,
    search_size="100",
    search_after=None,
    bearer=None,
):
```

#### Usage

```python
# Find objects where class = surface
search_results = sumo.search(query="class:surface", search_size="10")

# Get child objects for a specific object
parent_id = "1234"
children = sumo.search(query=f"_sumo.parent_object:{parent_id}")

# Get buckets for child object classes (i.e surface, table, polygon)
# This will return a count for every class value
buckets = sumo.search(
    query=f"_sumo.parent_object:{parent_id}",
    buckets=["class.keyword"]
)
```

### searchroot()

Search for parent objects (object without parent)

#### Parameters

```python
def searchroot(
    self,
    query,
    select=None,
    buckets=None,
    search_from=0,
    search_size="100",
    bearer=None,
):
```

#### Usage

```python
# Get 3 top level objects for a specific user
peesv_objects = sumo.searchroot(
    query="fmu.case.user.id:peesv",
    search_size=3
)
```
