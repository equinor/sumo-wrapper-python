from ._call_sumo_surface_api import CallSumoSurfaceApi
import xtgeo
import os
import yaml
import json
import time
import io
import glob

"""

This file contains sketchy prototyping. NOT FOR PRODUCTION.

"""

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

class MetadataError(Error):
    """Raised when something went wrong reading from metadata"""
    pass

class DuplicateSumoEnsemblesError(Error):
    """Raised when program finds more than one Sumo ensemble with the same fmu_ensemble_id"""
    pass

class SumoDeleteFailed():
    """Raised when a delete job failed"""
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
        """Establish the connection with Sumo API, take user through 2FA."""

        api = CallSumoSurfaceApi()
        api.get_bear_token()

        return api


class EnsembleOnDisk:
    """
    Class to hold information about an ERT run either on disk.
    """

    def __init__(self, manifest_path:str, api=None):
        """
        manifest_path (str): Path to manifest for ensemble
        api (SumoConnection instance): Connection to Sumo. Will be established
                                       if needed, and not passed. Pass the api
                                       to avoid multiple authentications if this
                                       class is used in a script.
        """

        print('INIT EnsembleOnDisk')

        self._manifest = self._load_manifest(manifest_path)
        self._fmu_id = None
        self._files = []
        self._api = api
        self._sumo_ensemble_id = None

    def __str__(self):
        s = f'{self.__class__}, {len(self._files)} files.'

        if self._sumo_ensemble_id is not None:
            s += f'\nInitialized on Sumo. Sumo_ID: {self._sumo_ensemble_id}'
        else:
            s += '\nNot initialized on Sumo.'

        s += '\nFMU casename: {}'.format(self.casename)

        return s

    def __repr__(self):
        return str(self.__str__)

    @property
    def api(self):
        if self._api is None:
            _A = SumoConnection()
            self._api = _A.api
        return self._api

    @property
    def manifest(self):
        return self._manifest

    @property
    def casename(self):
        return self._manifest.get('case')

    @property
    def sumo_ensemble_id(self):
        if self._sumo_ensemble_id is None:
            self._sumo_ensemble_id = self._get_sumo_ensemble_id()
        return self._sumo_ensemble_id

    @property
    def fmu_id(self):
        if self._fmu_id is None:
            self._fmu_id = self._get_fmu_id()
        return self._fmu_id

    @property
    def files(self):
        return self._files

    def add_files(self, searchstring):
        """Add files to the ensemble, based on searchstring"""
        file_paths = self._find_file_paths(searchstring)
        self._files += [FileOnDisk(path=file_path) for file_path in file_paths]

    def _find_file_paths(self, searchstring):
        """Given a searchstring, return yielded valid files as list
        of FileOnDisk instances"""
        files = [f for f in glob.glob(searchstring) if os.path.isfile(f)]
        if len(files) == 0:
            print('No files found! Bad searchstring?')
            print('Searchstring: {}'.format(searchstring))
        return files

    def _get_sumo_ensemble_id(self):
        """Call sumo, check if the ensemble is already there. Use fmu_ensemble_id for this."""

        print('Getting SumoID')

        # search for all ensembles on Sumo
        E = EnsemblesOnSumo(api=self.api)
        matches = [m.sumo_ensemble_id for m in E.ensembles if m.fmu_id == self.fmu_id]

        if len(matches) == 0:
            print('No matching ensembles found on Sumo --> Not registered on Sumo')
            print('Registering ensemble on Sumo')
            sumo_ensemble_id = self._upload_manifest(self.manifest)
            print('Ensemble registered. SumoID: {}'.format(sumo_ensemble_id))
            return sumo_ensemble_id

        if len(matches) == 1:
            print('Found one matching ensemble on Sumo --> Registered on Sumo')
            return matches[0]

        # TEMP workaround, will not allow this in prod
        print('WARNING! {} ensembles on Sumo with the same FMU_ID. Returning the first.'.format(len(matches)))
        for match in matches:
            print(match)
        return matches[0]
        #raise DuplicateSumoEnsemblesError(f'Found {len(matches)} ensembles with the same ID on Sumo')

    def _upload_manifest(self, manifest:dict):
        """Given a manifest dict, upload it to Sumo"""
        print('UPLOAD MANIFEST')
        returned_object_id = self.api.save_top_level_json(json=manifest)
        return returned_object_id

    def _load_manifest(self, manifest_path:str):
        """Given manifest path, load the yaml file, return dict"""

        if not os.path.isfile(manifest_path):
            raise IOError('File does not exist: {}'.format(manifest_path))

        with open(manifest_path, 'r') as stream:
            yaml_data = yaml.safe_load(stream)

        return yaml_data

    def _get_fmu_id(self):
        """Look up and return ensemble_id from manifest"""
        eid = self.manifest.get('')

    def upload(self, upload_files=True):
        """Trigger upload of ensemble"""
        if self._sumo_ensemble_id is None:
            self._sumo_ensemble_id = self._get_sumo_ensemble_id()

        if upload_files:
            UPLOAD_FILES(files=self.files, sumo_ensemble_id=self._sumo_ensemble_id, api=self.api)

        print('Uploaded')

class EnsemblesOnSumo:
    """Class for holding multiple ensembles on Sumo"""

    def __init__(self, api=None):

        print('INIT EnsemblesOnSumo')

        if api is None:
            _A = SumoConnection()
            self.api = _A.api
        else:
            self.api = api

        self.ensembles = self.get_ensembles()

    def get_ensembles(self):
        """Get list of ensembles from Sumo differentiated by their unique ID"""

        print('get_ensembles()')
        query = "*"
        select = 'source,field'
        buckets = 'source'
        search_results = self.api.searchroot(query, select=select, buckets=buckets)
        hits = search_results.get('hits').get('hits')

        if hits is None:
            raise IOError('Unexpected response from Sumo. "hits" was not included.')
            #return []

        if len(hits) == 0:
            print(f'No hits for query {query}')
            return []

        hit_ids = [h.get('_id') for h in hits]

        ensembles = [EnsembleOnSumo(sumo_ensemble_id=_id, api=self.api) for _id in hit_ids]

        return ensembles


class EnsembleOnSumo:
    """Class for holding an ensemble stored on Sumo"""

    def __init__(self, sumo_ensemble_id:str, api=None):
        """
        sumo_ensemble_id: The unique ID for the specific run assigned by Sumo

        Possible source of confusion: The ensemble_id is the one Sumo has assigned, not
        the one that was given from the source.
        """

        print('INIT EnsembleOnSumo. sumo_ensemble_id given: {}'.format(sumo_ensemble_id))

        self.sumo_ensemble_id = sumo_ensemble_id
        self._fmu_id = None
        self._casename = None

        if api is None:
            _A = SumoConnection()
            self.api = _A.api
        else:
            self.api = api

        self._manifest = None

    def __repr__(self):
        return f"<EnsembleOnSumo> - SumoID: {self.sumo_ensemble_id}"

    @property
    def manifest(self):
        if self._manifest is None:
            self._manifest = self._get_manifest(sumo_ensemble_id=self.sumo_ensemble_id)
        return self._manifest

    @property
    def fmu_id(self):
        if self._fmu_id is None:
            self._fmu_id = self.manifest.get('fmu_ensemble_id')
        return self._fmu_id

    @property
    def casename(self):
        if self._casename is None:
            self._casename = self.manifest.get('case')
        return self._casename

    def delete(self):
        """Delete this ensemble from Sumo"""
        print(self.sumo_ensemble_id)
        print(type(self.sumo_ensemble_id))
        response = self.api.delete_object(self.sumo_ensemble_id)

        if response != 'ok':
            print('\n')
            print(response)
            raise DeleteFailed()

        return response

    def _get_manifest(self, sumo_ensemble_id:str):
        """Get and store manifest (metadata) for this run"""

        data_from_sumo = self.api.get_json(object_id=sumo_ensemble_id)
        return data_from_sumo

class FilesOnDisk:

    def __init__(self, searchstring:str, ensemble_id:str, api=None):
        """
        Class for many files, which in turn calls the FileOnDisk class.
        The purpose of this class is to facilitate uploading of multiple 
        objects on the same authentication.

        searchstring (str): Globable searchstring for files to initialize
        """

        self.ensemble_id = ensemble_id

        if api is None:
            _A = SumoConnection()
            self.api = _A.api
        else:
            self.api = api

        self.files = self.load_files(searchstring)

    def __repr__(self):
        return '<Sumo.FilesOnDisk>\n{} files initialized.'.format(len(self.files))

    def load_files(self, file_paths:list):
        """Given a searchstring, return a list of FileOnDisk instances
        for each file found"""

        file_paths = [f for f in glob.glob(searchstring) if os.path.isfile(f)]
        return [FileOnDisk(path) for path in file_paths]

    def upload(self):
        """Trigger upload of all files"""

        UPLOAD_FILES(files=files, api=api)

class FileOnDisk:

    def __init__(self, path:str, metadata_path=None):
        """
        path (str): Path to file
        metadata_path (str): Path to metadata file. If not provided, 
                             path will be derived from file path.
        """

        if metadata_path is None:
            self.metadata_path = self.path_to_yaml_path(path)
        else:
            self.metadata_path = metadata_path

        self._metadata = self.get_metadata(self.metadata_path)
        self._bytestring = self.file_to_bytestring(path)
        self._path = path
        self._sumo_ensemble_id = None
        self._basename = None
        self._dirname = None
        self._dtype = None
        self._fformat = None

    def __repr__(self):
        s =  f'\n# {self.__class__}'
        s += f'\n# Diskpath: {self.path}'
        s += f'\n# Basename: {self.basename}'
        s += f'\n# Bytestring length: {len(self.bytestring)}'
        s += f'\n# Data type: {self.dtype}'
        s += f'\n# File format: {self.fformat}'

        if self.sumo_ensemble_id is None:
            s += '\n# Not uploaded to Sumo'
        else:
            s += f'\n# Uploaded to Sumo. Sumo_ID: {self.sumo_ensemble_id}'

        s += '\n\n'

        return s

    @property
    def sumo_ensemble_id(self):
        return self._sumo_ensemble_id

    @sumo_ensemble_id.setter
    def sumo_ensemble_id(self, sumo_ensemble_id):
        self._sumo_ensemble_id = sumo_ensemble_id

    @sumo_ensemble_id.deleter
    def sumo_ensemble_id(self):
        self._sumo_ensemble_id = None

    @property
    def path(self):
        return self._path

    @property
    def basename(self):
        if not self._basename:
            self._basename = os.path.basename(self.path)
        return self._basename

    @property
    def dirname(self):
        if not self._dirname:
            self._dirname = os.path.dirname(self.path)
        return self._dirname

    @property
    def dtype(self):
        if not self._dtype:
            self._dtype = self._get_dtype()
        return self._dtype

    @property
    def fformat(self):
        if not self._fformat:
            self._fformat = self._get_fformat()
        return self._fformat

    @property
    def metadata(self):
        return self._metadata

    @property
    def bytestring(self):
        return self._bytestring

    def _get_dtype(self):
        """Look up file format from metadata"""

        dtype = self.metadata.get('data', {}).get('type')

        if dtype is None:
            #logging.error('Could not get file format from metadata')
            #logging.error('File: {}'.format(self.path))
            #logging.error('Metadata file: {}'.format(self.metadata_path))
            raise MetadataError('Could not get file format')

        return dtype

    def _get_fformat(self):
        """Look up file format from metadata"""

        fformat = self.metadata.get('data', {}).get('format')

        if fformat is None:
            #logging.error('Could not get file format from metadata')
            #logging.error('File: {}'.format(self.path))
            #logging.error('Metadata file: {}'.format(self.metadata_path))
            raise MetadataError('Could not get file format')

        return fformat

    def path_to_yaml_path(self, path):
        """
        Given a path, return the corresponding yaml file path
        according to FMU standards.
        /my/path/file.txt --> /my/path/.file.txt.yaml
        """

        dirname = os.path.dirname(path)
        basename = os.path.basename(path)

        return os.path.join(dirname, f'.{basename}.yaml')

    def get_metadata(self, metadata_path):
        return self.parse_yaml(metadata_path)

    def parse_yaml(self, path):
        if not os.path.isfile(path):
            raise IOError('File does not exist: {}'.format(path))
        with open(path, 'r') as stream:
            data = yaml.safe_load(stream)
        return data

    def file_to_bytestring(self, path):
        """
        Given an path to a file, read as bytes,
        return bytestring. 
        """

        with open(path, 'rb') as f:
            bytestring = f.read()

        return bytestring

def UPLOAD_FILES(files:list, sumo_ensemble_id:str, api=None):
    """
    Upload files, including JSON, to specified ensemble

    files: list of FileOnDisk objects
    sumo_ensemble_id: sumo_ensemble_id for the parent ensemble

    Upload is kept outside classes to ease multithreading.
    """

    def _upload_metadata(api, metadata:dict, object_id:str):
        metadata = _clean_metadata(metadata)
        returned_object_id = api.save_child_level_json(json=metadata, object_id=object_id)
        return returned_object_id

    def _upload_bytestring(api, object_id, blob):
        returned_object_id = api.save_blob(object_id=object_id, blob=blob)
        return returned_object_id

    def _datetime_to_str(metadata:dict):
        """Temporary (?) fix for datetime in incoming yaml, not serializable."""
        datetime = metadata.get('datetime', None)
        if datetime:
            del(metadata['datetime'])
        return metadata

    def _clean_metadata(metadata:dict):
        metadata = _datetime_to_str(metadata)
        return metadata

    _t0 = time.perf_counter()

    for file in files:
        print(f'  Uploading {file.basename}')
        print('  > metadata')
        object_id = _upload_metadata(api=api, metadata=file.metadata, object_id=sumo_ensemble_id)
        print('  > bytestring')
        object_id_blob = _upload_bytestring(api=api, blob=file.bytestring, object_id=object_id)
        print(' OK --> object_id: {}\n'.format(object_id))

    _t1 = time.perf_counter()
    _dt = _t1-_t0

    print(f'Uploaded {len(files)} surfaces in {_dt:0.4f} seconds')

    return {'elements' : [s.basename for s in files],
            'sumo_ensemble_id' : sumo_ensemble_id,
            'count' : len(files),
            'time_start' : _t0,
            'time_end' : _t1,
            'time_elapsed' : _dt,}


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