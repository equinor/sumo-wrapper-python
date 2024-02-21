sumo-wrapper-python
###################

Short introduction
*******************

A thin python wrapper class that can be used by Sumo client applications to 
communicate with the Sumo core server. It has methods for GET, PUT, POST and DELETE, 
and handles authentication and automatic network retries. 

This is low-level and close to the Sumo API and primarily intended for developers. 
For usage in the FMU context, the higher-level alternative 
`fmu-sumo <https://fmu-sumo.readthedocs.io>`_ is recommended. 

The Sumo API is described at 
`https://main-sumo-prod.radix.equinor.com/swagger-ui/ <https://main-sumo-prod.radix.equinor.com/swagger-ui/>`_

The data model and schema is described at 
`https://fmu-dataio.readthedocs.io/en/latest/datamodel.html <https://fmu-dataio.readthedocs.io/en/latest/datamodel.html>`_

Information on Sumo can be found `here <https://doc-sumo-doc-prod.radix.equinor.com/>`_

Preconditions
*************

Access
------

For internal Equinor users: Apply for access to Sumo in Equinor AccessIT, search for Sumo.

Install
*******

For internal Equinor users, this package is included in the Komodo distribution. 
For other use cases it can be pip installed directly from PyPI:

.. code-block:: 

   pip install sumo-wrapper-python

Initialization
**************

.. code-block:: python

   from sumo.wrapper import SumoClient

   Sumo = SumoClient()

`token` logic
*************

No token provided: this will trigger 
an authentication process and then handles token, token refresh and
re-authentication as automatic as possible. This would be the most common
usecase. 

If an access token is provided in the `token` parameter, it will be used as long
as it's valid. An error will be raised when it expires.

If we are unable to decode the provided `token` as a JWT, we treat it as a
refresh token and attempt to use it to retrieve an access token.


Methods
*******

`SumoClient` has one method for each HTTP-method that is used in the Sumo
API: GET, PUT, POST and DELETE. In addition a method to get a blob client 
which handles blob contents. 

The methods accepts a path argument.  A path is the path to a 
Sumo `API <https://main-sumo-prod.radix.equinor.com/swagger-ui/>`_ method, for 
example "/search" or "/smda/countries". Path parameters can be added into
the path string, for example 

.. code-block:: python

   f"/objects('{case_uuid}')/search"

The Sumo API documentation is available from the Swagger button in 
the Sumo frontend, or you can use this link:
`https://main-sumo-prod.radix.equinor.com/swagger-ui/ <https://main-sumo-prod.radix.equinor.com/swagger-ui/>`_. 

Async methods
*************

`SumoClient` also has *async* alternatives `get_async`, `post_async`, `put_async` and `delete_async`.
These accept the same parameters as their synchronous counterparts, but have to be *awaited*.

Usage and examples
******************

.. code-block:: python

   from sumo.wrapper import SumoClient
   sumo = SumoClient()

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


.. toctree::
   :maxdepth: 2
   :caption: Contents:

