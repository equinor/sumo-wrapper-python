from .call_sumo_surface_api import CallSumoSurfaceApi
from xtgeo import RegularSurface
import os
import yaml
import json
import time

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

class IterationOnDisk:
    def __init__(self, manifest_path:str):
        self._manifest = self._load_manifest(manifest_path)
        self.api = CallSumoSurfaceApi()
        self.api.get_bear_token()

    @property
    def manifest(self):
        return self._manifest

    def upload(self):
        """Upload the manifest to initialize this iteration on Sumo"""

        object_id = self._upload_manifest(self.manifest)

        return object_id

    def _upload_manifest(self, manifest:dict):
        """Given a manifest dict, upload it to Sumo"""
        post_object_results = self.api.save_top_level_json(json=manifest)
        result = post_object_results.get('result', None)
        if not result == 'created':
            raise SumoObjectNotCreated
        return post_object_results.get('_id')


    def _load_manifest(self, manifest_path:str):
        """Given manifest path, load the yaml file, return dict"""

        if not os.path.isfile(manifest_path):
            raise IOError('File does not exist: {}'.format(manifest_path))

        with open(manifest_path, 'r') as stream:
            yaml_data = yaml.safe_load(stream)

        return yaml_data



class SurfacesOnDisk:
    def __init__(self, surface_paths:list, iteration_id:str):
        """
        Class for many surfaces, which in turn calls the Surface class
        The purpose of this class is to facilitate uploading of multiple
        surfaces on the same authentication.

        surfaces: List of filepaths to IRAP Binary surfaces

        """

        self.iteration_id = iteration_id
        self.api = CallSumoSurfaceApi()
        self.api.get_bear_token()
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
            print('Uploading {}'.format(surface.basename))
            object_id = self._upload_metadata(metadata=surface.metadata, iteration_id=self.iteration_id)
            object_id_blob = self._upload_bytestring(object_id=object_id, blob=surface.bytestring)

        _t1 = time.perf_counter()

        _dt = _t1-_t0

        print(f'Uploaded {len(self.surfaces)} surfaces in {_dt:0.4f} seconds')

        return {'elements' : [s.basename for s in self.surfaces],
                'count' : len(self.surfaces),
                'time_start' : _t0,
                'time_end' : _t1,
                'time_elapsed' : _dt,}

    def _upload_metadata(self, metadata, iteration_id:str):
        metadata = self._clean_metadata(metadata)
        returned_object_id = self.api.save_child_level_json(json=metadata, object_id=iteration_id)
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


class SurfaceOnSumo:
    """Class for handling surfaces stored on Sumo"""

    def __init__(self, object_id):
        self.api = CallSumoSurfaceApi()
        self.api.get_bear_token()
        self._bytestring = None

        self.metadata, self.bytestring = self.get_from_sumo(object_id)

        self.regularsurface = self.bytestring_to_regularsurface(self.bytestring)

    def get_from_sumo(self, object_id):
        """Download surface with this object_id from Sumo"""
        _metadata = self.get_metadata(object_id=object_id)
        _bytestring = self.get_bytestring(object_id=object_id)

        return _metadata, _bytestring

    def get_metadata(self, object_id):
        result = self.api.get_json(object_id=object_id)
        found = result.get('found', None)
        if not found:
            raise SumoObjectNotFound
        return result.get('_id')

    def get_bytestring(self, object_id):
        result = self.api.get_blob(object_id=object_id)
        return result

    def bytestring_to_regularsurface(self, bytestring):
        """Given a downloaded bytestring, make xtgeo.RegularSurface,
        return xtgeo.RegularSurface object"""

        regularsurface = xtgeo.RegularSurface(bytestring)
        return regularsurface

    def to_file(self, filename):
        """
        Store the downloaded surface as IRAP Binary to
        given filename
        """

        self.regularsurface.to_file(filename, fformat='irap binary')