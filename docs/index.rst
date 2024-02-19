.. sumo-wrapper-python documentation master file, created by
   sphinx-quickstart on Wed Jun  8 15:11:37 2022.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

####################################
sumo-wrapper-python
####################################

A thin python wrapper class that can be used by Sumo client applications to 
communicate with the Sumo core server. It has methods for GET, PUT, POST and DELETE, 
and handles authentication and automatic network retries. 

A higher level alternative is available 
here: `fmu-sumo <https://fmu-sumo.readthedocs.io>`_ 

API is described at `https://main-sumo-prod.radix.equinor.com/swagger-ui/ <https://main-sumo-prod.radix.equinor.com/swagger-ui/>`_

Access
------

For internal Equinor users: Apply for Equinor AccessIT, search for SUMO.

Install
-------

For internal Equinor users, this package is available through the Komodo
distribution. In other cases it can be pip installed:

.. code-block:: 

   pip install sumo-wrapper-python


SumoClient
----------

This class is for communicating with the Sumo core server using the Sumo API. 


Initialization
^^^^^^^^^^^^^^

.. code-block:: python

   from sumo.wrapper import SumoClient

   Sumo = SumoClient()


`token` logic
^^^^^^^^^^^^^

No token provided: this will trigger 
an authentication process and then handles token, token refresh and
re-authentication as automatic as possible.

If an access token is provided in the `token` parameter, it will be used as long
as it's valid. An error will be raised when it expires.

If we are unable to decode the provided `token` as a JWT, we treat it as a
refresh token and attempt to use it to retrieve an access token.


Methods
^^^^^^^

`SumoClient` has one method for each HTTP-method that is used in the Sumo
API: GET, PUT, POST and DELETE. 
The Sumo API documentation is available from the Swagger button in 
the Sumo frontend. 

Methods accepts a path argument. Path parameters can be interpolated into
the path string. 

Async methods
^^^^^^^^^^^^^

`SumoClient` also has *async* alternatives `get_async`, `post_async`, `put_async` and `delete_async`.
These accept the same parameters as their synchronous counterparts, but have to be *awaited*.

Example
^^^^^^^^

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

.. automodule:: sumo.wrapper.sumo_client
   :members:
   :undoc-members:
   :show-inheritance:

..
   Indices and tables
   ==================

   * :ref:`genindex`
   * :ref:`modindex`
   * :ref:`search`