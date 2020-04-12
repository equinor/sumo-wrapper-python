from ._call_sumo_surface_api import CallSumoSurfaceApi
import xtgeo
import os
import yaml
import json
import time
import io

class Error(Exception):
   """Base class for other exceptions"""
   pass

class SumoObjectNotCreated(Error):
   """Raised when and object was not created"""
   pass

class SumoObjectNotFound(Error):
   """Raised when the requested object was not found"""
   pass

class SumoObjectNotDeleted(Error):
    """Raised when an object was not deleted"""
    pass

class NoMetadataError(Error):
    """Raised when a specific surface did not have
    corresponding metadata"""
    pass


class SumoConnection:
    """Object to hold authentication towards Sumo"""

    def __init__(self):
        self._api = None

    @property
    def api(self):
        if self._api is None:
            self._api = self._establish_connection()
        return self._api

    def refresh(self):
        """Re-create the connection"""
        self._api = self._establish_connection()        

    def _establish_connection(self):
        """Establish the connection with Sumo API, take user through
        2-factor authentication. Keep the connection."""

        api = CallSumoSurfaceApi()
        api.get_bear_token()

        return api



class EnsembleOnDisk:
    """Class to hold information about an ERT run on disk"""
    def __init__(self, manifest_path:str, api=None):
        self._manifest = self._load_manifest(manifest_path)

        if api is None:
            _A = SumoConnection()
            self.api = _A.api
        else:
            self.api = api

    @property
    def manifest(self):
        return self._manifest

    def upload(self):
        """Upload the manifest to initialize this run on Sumo"""

        object_id = self._upload_manifest(self.manifest)

        return object_id

    def _upload_manifest(self, manifest:dict):
        """Given a manifest dict, upload it to Sumo"""
        returned_object_id = self.api.save_top_level_json(json=manifest)
        return returned_object_id


    def _load_manifest(self, manifest_path:str):
        """Given manifest path, load the yaml file, return dict"""

        if not os.path.isfile(manifest_path):
            raise IOError('File does not exist: {}'.format(manifest_path))

        with open(manifest_path, 'r') as stream:
            yaml_data = yaml.safe_load(stream)

        return yaml_data

class EnsemblesOnSumo:
    """Class for holding multiple ensembles on Sumo"""

    def __init__(self, api=None):

        if api is None:
            _A = SumoConnection()
            self.api = _A.api
        else:
            self.api = api

        self.ensembles = self.get_ensembles()


    def get_ensembles(self):
        """Get list of ensembles from Sumo differentiated by their unique ID"""

        query = "*"
        search_results = self.api.search(query)
        hits = search_results.get('hits').get('hits')

        if hits is None:
            print(f'hits not in search_results...')

        if len(hits) == 0:
            print(f'No hits for query {query}')

        hit_ids = [h.get('_id') for h in hits]

        ensembles = [EnsembleOnSumo(_id=_id, api=self.api) for _id in hit_ids]

        return ensembles

class EnsembleOnSumo:
    """Class for holding an ensemble stored on Sumo"""

    def __init__(self, _id:str, api=None):
        """
        sumo_ensemble_id: The unique ID for the specific run assigned by Sumo

        Possible source of confusion: The ensemble_id is the one Sumo has assigned, not
        the one that was given from the source.

        """

        self._id = _id

        if api is None:
            _A = SumoConnection()
            self.api = _A.api
        else:
            self.api = api

        self._metadata = None

        #self.surfaces = self._find_surfaces(ensemble_id=ensemble_id)

    def __repr__(self):
        return f"<EnsembleOnSumo> - ID: {self._id}"

    @property
    def metadata(self):
        if self._metadata is None:
            self._metadata = self._get_metadata(_id=self._id)
        return self._metadata

    def _get_metadata(self, _id:str):
        """Get and store metadata for this run"""

        data_from_sumo = self.api.get_json(object_id=_id)
        return data_from_sumo


class SurfacesOnDisk:
    def __init__(self, surface_paths:list, run_id:str, api=None):
        """
        Class for many surfaces, which in turn calls the Surface class
        The purpose of this class is to facilitate uploading of multiple
        surfaces on the same authentication.

        surfaces: List of filepaths to IRAP Binary surfaces

        """

        self.run_id = run_id

        if api is None:
            _A = SumoConnection()
            self.api = _A.api
        else:
            self.api = api

        self.surfaces = self.load_surfaces(surface_paths)

    def load_surfaces(self, surface_paths:list):
        """Load the surfaces to XTgeo.RegularSurface objects
         + metadata from disk.
        Return as a dictionary with the path as key"""

        return [SurfaceOnDisk(path) for path in surface_paths]

    def upload(self):
        """Upload the surfaces"""

        _t0 = time.perf_counter()
        for surface in self.surfaces:
            object_id = self._upload_metadata(metadata=surface.metadata, run_id=self.run_id)
            object_id_blob = self._upload_bytestring(object_id=object_id, blob=surface.bytestring)
            print('{} - object_id: {}'.format(surface.basename, object_id))

        _t1 = time.perf_counter()

        _dt = _t1-_t0

        print(f'Uploaded {len(self.surfaces)} surfaces in {_dt:0.4f} seconds')

        return {'elements' : [s.basename for s in self.surfaces],
                'count' : len(self.surfaces),
                'time_start' : _t0,
                'time_end' : _t1,
                'time_elapsed' : _dt,}

    def _upload_metadata(self, metadata, run_id:str):
        metadata = self._clean_metadata(metadata)
        returned_object_id = self.api.save_child_level_json(json=metadata, object_id=run_id)
        return returned_object_id

    def _upload_bytestring(self, object_id, blob):
        returned_object_id = self.api.save_blob(object_id=object_id, blob=blob)
        return returned_object_id

    def _datetime_to_str(self, metadata:dict):
        """Temporary (?) fix for datetime in incoming yaml, not serializable."""
        datetime = metadata.get('datetime', None)
        if datetime:
            #metadata['datetime'] = str(datetime)
            del(metadata['datetime'])

        return metadata

    def _clean_metadata(self, metadata:dict):

        metadata = self._datetime_to_str(metadata)

        return metadata


    def _is_json(self, d:dict):
        try:
            json.loads(d)
            return True
        except:
            return False


class SurfaceOnDisk:
    """Class for handling one single surface from disk"""
    def __init__(self, surface_path:str):
        self._metadata_yaml = self.load_metadata(surface_path)
        self._metadata = self._metadata_yaml #self.dict_to_json(self._metadata_yaml)
        self._bytestring = self.surface_to_bytestring(surface_path)
        self._basename = os.path.basename(surface_path)

    @property
    def basename(self):
        return self._basename

    @property
    def bytestring(self):
        return self._bytestring

    @property
    def metadata_yaml(self):
        return self._metadata_yaml

    @property
    def metadata(self):
        return self._metadata

    def load_surface(self, path):
        """Given a path to a single IRAP binary file, load
        it to RegularSurface object, return the object"""

        return RegularSurface(path)

    def load_metadata(self, path):
        """
        Given a path to a single IRAP binary file, load
        the corresponding yaml-file according to FMU standard
        rules:

        path = /my/dir/surface.gri
        ypath = /my/dir/.surface.gri.yaml

        """

        _d = os.path.dirname(path)
        _b = os.path.basename(path)

        ypath = os.path.join(_d, f'.{_b}.yaml')

        with open(ypath, 'r') as stream:
            ydata = yaml.safe_load(stream)

        return ydata

    def dict_to_json(self, data:dict):
        """
        Get dict, return json object 
        """

        return json.dumps(data)


    def surface_to_bytestring(self, path):
        """
        Given an path to an irap binary file, read as bytes,
        return bytestring. 
        """

        with open(path, 'rb') as f:
            bytestring = f.read()

        return bytestring


class SurfacesOnSumo:
    """Class for handling surfaces stored on Sumo. """


    def __init__(self, parent_id:str, api=None):
        """
        parent_id: The unique ID for the specific run

        """

        self.parent_id = parent_id

        if api is None:
            _A = SumoConnection()
            self.api = _A.api
        else:
            self.api = api

        self.surfaces = self._find_surfaces(parent_id=parent_id)

    def __repr__(self):
        print(f'''
            <SurfacesOnSumo>
            Surfaces initialized: {len(self.surfaces)}
            ''')

    def _find_surfaces(self, parent_id:str):
        """Send a search query to Sumo, return object ID list"""

        print(' --> finding surfaces on Sumo')
        query = f"_sumo.parent_object:{parent_id}"
        search_results = self.api.search(query=query)
        #def search(self, query, select=None, buckets=None, search_from=0, search_size=10, bearer=None):

        hits = search_results.get('hits').get('hits')

        print(' --> Initializing Surface objects')
        surfaces = [SurfaceOnSumo(object_id=hit.get('_id'), api=self.api) for hit in hits]

        print(' --> Returning list of Surface objects')
        return surfaces


class SurfaceOnSumo:
    """Class for handling surfaces stored on Sumo"""

    def __init__(self, object_id, api=None):

        if api is None:
            _A = SumoConnection()
            self.api = _A.api
        else:
            self.api = api
        
        self.object_id = object_id
        self._metadata = None
        self._bytestring = None
        self._regularsurface = None

    @property
    def metadata(self):
        if self._metadata is None:
            self._metadata = self.get_metadata(object_id=self.object_id)
        return self._metadata

    @property
    def bytestring(self):
        if self._bytestring is None:
            self._bytestring = self.get_bytestring(object_id=self.object_id)
        return self._bytestring

    @property
    def regularsurface(self):
        if self._regularsurface is None:
            self._regularsurface = self.bytestring_to_regularsurface(self.bytestring)
        return self._regularsurface

    def __repr__(self):
        return f"""ID: {self.object_id}"""

    def get_from_sumo(self, object_id):
        """Download surface with this object_id from Sumo"""

        print(' --> Downloading metadata')
        _metadata = self.get_metadata(object_id=object_id)
        print('     --> Done')
        print(' --> Downloading bytestring')
        _bytestring = self.get_bytestring(object_id=object_id)
        print('     --> Done')

        return _metadata, _bytestring

    def get_metadata(self, object_id):
        _t0 = time.perf_counter()

        result = self.api.get_json(object_id=object_id)
        found = result.get('found', None)
        if not found:
            raise SumoObjectNotFound

        _t1 = time.perf_counter()
        _dt = _t1-_t0
        print(f'Done in {_dt:0.4f} seconds')

        return result.get('_source')   # <-- as incoming yaml

    def get_bytestring(self, object_id):
        print('  --> Bytestring from Sumo')
        _t0 = time.perf_counter()
        result = self.api.get_blob(object_id=object_id)
        _t1 = time.perf_counter()
        _dt = _t1-_t0
        print(f'    --> Done, {_dt:0.4f} seconds')
        return result

    def bytestring_to_regularsurface(self, bytestring):
        """Given a downloaded bytestring, make xtgeo.RegularSurface,
        return xtgeo.RegularSurface object"""

        _t0 = time.perf_counter()        
        print('  --> Bytestring --> xtgeo.RegularSurface()')
        regularsurface = xtgeo.RegularSurface(io.BytesIO(bytestring))
        _dt = time.perf_counter() - _t0
        print(f'    --> Done, {_dt:0.4f} seconds')
        return regularsurface

    def to_file(self, filename):
        """
        Store the downloaded surface as IRAP Binary to
        given filename
        """

        self.regularsurface.to_file(filename, fformat='irap binary')