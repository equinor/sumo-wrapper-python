# sumo-wrapper-python

Python wrappers for Sumo APIs

Want to contribute? Read our [contributing](./CONTRIBUTING.md) guidelines

## Access

Equinor AccessIT: search for SUMO

## Install

    pip install sumo-wrapper-python

For internal Equinor users, this package is available through the Komodo
distribution.

# SumoClient

A thin wrapper class for the Sumo API.

### Initialization

```python
from sumo.wrapper import SumoClient

Sumo = SumoClient(env="dev")
```

### Parameters

```python
class SumoClient:
    def __init__(
        self,
        env: str,
        token: str = None,
        interactive: bool = False,
        devicecode: bool = False,
        verbosity: str = "CRITICAL",
        retry_strategy=RetryStrategy(),
    ):
```

- `env`: Sumo environment: "dev", "prod"
- `token`: bearer token or refresh token
- `interactive`: use interactive flow when authenticating
- `devicecode`: use device code flow when authenticating
- `verbosity`: "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"
- `retry_strategy`: network retry strategy

###### `token` logic

The most used option is to not provide a token: this will trigger 
an authentication process and then handles token, token refresh and
re-authentication as automatic as possible.

If an access token is provided in the `token` parameter, it will be used as long
as it's valid. An error will be raised when it expires.

If we are unable to decode the provided `token` as a JWT, we treat it as a
refresh token and attempt to use it to retrieve an access token.


## Methods

`SumoClient` has one method for each HTTP-method that is used in the Sumo
API. The Sumo API documentation is available from the Swagger button in the Sumo frontend. 

All methods accepts a path argument. Path parameters can be interpolated into
the path string. Example:

```python
object_id = "1234"

# GET/objects('{objectid}')
sumo.get(f"/objects('{object_id}')")
```

### get(path, \*\*params)

Performs a GET-request to Sumo. Accepts query parameters as keyword
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

Performs a POST-request to Sumo. Accepts json and blob, but not both at the
same time.

```python
# Upload new parent object
parent_object = sumo.post("/objects", json=parent_meta_data)

# Upload child object
parent_id = parent_object["_id"]

child_object = sumo.post(f"/objects('{parent_id}')", json=child_meta_data)
```

### put(path, json, blob)

Performs a PUT-request to Sumo. Accepts json and blob, but not both at the
same time.

```python
# Upload blob to child object
child_id = child_object["_id"]

sumo.put(f"/objects('{child_id}')/blob", blob=blob)
```

### delete(path)

Performs a DELETE-request to Sumo.

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

## Example

```python
from sumo.wrapper import SumoClient
sumo = SumoClient(env="prod")

# The line above will trigger the authentication process, and 
# the behaviour depends on how long since your last login. 
# It could re-use existing login or it could take you through 
# a full Microsoft authentication process including  
# username, password, two-factor. 

# List your Sumo permissions:
print("My permissions:", sumo.get("/userpermissions").json())

# Get the first case from the list of cases you have access to:
case = sumo.get("/searchroot").json()["hits"]["hits"][0]
print("Case metadata:", case["_source"])
case_uuid = case["_source"]["fmu"]["case"]["uuid"]
print("Case uuid: ", case_uuid)

# Get the first child object:
child = sumo.get(f"/objects('{case_uuid}')/search").json()["hits"]["hits"][0]
print("Child metadata", child["_source"])
child_uuid = child["_id"]
print("Child uuid: ", child_uuid)

# Get the binary of the child
binary_object = sumo.get(f"/objects('{child_uuid}')/blob").content
print("Size of child binary object:", len(binary_object))
```
