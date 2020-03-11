# sumo-surface-python
Development of Python wrappers for Sumo APIs


## Install by runing: 
    
    pip install git+ssh://git@github.com/equinor/sumo-surface-python.git@master
    
## Example code:

    from sumo.call_sumo_surface_api import CallSumoSurfaceApi
    
    api = CallSumoSurfaceApi();
    bearer = api.get_bear_token()
    api.get_health_json(bearer)
