# sumo-wrapper-python

Python wrappers for Sumo APIs

Want to contribute? Read our [contributing](./CONTRIBUTING.md) guidelines

## Install:

    pip install sumo-wrapper-python

For internal Equinor users, this package is available through the Komodo
distribution.

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
    - [post(path, json, blob, params)](#postpath-json-blob-params)
    - [put(path, json, blob)](#putpath-json-blob)
    - [delete(path)](#deletepath)
  - [Async methods](#async-methods)

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

### post(path, json, blob, params)

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
