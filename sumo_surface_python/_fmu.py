import CallSumoSurfaceApi
from xtgeo import RegularSurface

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

class SurfacesOnDisk:
    def __init__(self, surface_paths:list):
        """
        Class for many surfaces, which in turn calls the Surface class
        The purpose of this class is to facilitate uploading of multiple
        surfaces on the same authentication.

        surfaces: List of filepaths to IRAP Binary surfaces

        """

        self.surfaces = self.load_surfaces(surface_paths)
        self.api = CallSumoSurfaceApi()
        self.api.get_bear_token()

    def load_surfaces(self, surface_paths:list):
        """Load the surfaces to XTgeo.RegularSurface objects
         + metadata from disk.
        Return as a dictionary with the path as key"""

        return [LocalSurface(path) for path in surface_paths]

    def upload(self):
        """Upload the surfaces"""
        for surface in surfaces:
            object_id = self.upload_metadata(surface.metadata)
            object_id_blob = self.upload_bytestring(object_id=object_id, blob=surface.blob)

        print('********** UPLOAD OK ***********')

    def upload_metadata(self, contents):
        result = self.api.save_top_level_json(json=contents).get('result', None)
        if not result == 'created':
            raise SumoObjectNotCreated
        return result

    def upload_bytestring(self, object_id, blob):
        result = self.api.save_blob(object_id=object_id, blob=blob)



class SurfaceOnDisk:
    """Class for handling one single surface from disk"""
    def __init__(self, surface_path:str):
        self._metadata = self.load_metadata(surface_path)
        self._bytestring = self.surface_to_bytestring(surface_path)

    @property
    def bytestring(self):
        return self._bytestring

    @property
    def metadata(self):
        return self._metadata

    def load_surface(self, path):
        """Given a path to a single IRAP binary file, load
        it to RegularSurface object, return the object"""

        return RegularSurface(path)

    def load_metadata(self, path):
        """Given a path to a single IRAP binary file, load
        the corresponding yaml-file according to FMU standard
        rules:

        path = /my/dir/surface.gri
        ypath = /my/dir/.surface.gri.yaml

        """

        _d = os.path.dirname(path)
        _b = os.path.basename(path)

        ypath = os.path.join(_d, f'.{_b}.yaml')

        with open(ypath, 'r') as stream:
            ydata = yaml.safeload(ypath)

        return ydata        

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
        self._regularsurface = None

        self.metadata, self.bytestring = self.get_from_sumo(object_id)
        

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

    def to_xtgeo(self):
        """Return the downloaded bytestring as an 
        xtgeo.RegularSurface object"""

        pass

    def to_file(self, filename):
        """
        Store the downloaded surface as IRAP Binary to
        given filename
        """

        self.regularsurface.to_file(filename, fformat='irap binary')