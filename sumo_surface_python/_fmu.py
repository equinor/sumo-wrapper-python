import xtgeo
import os
import yaml
import json
import time
import io
import glob
import datetime

from concurrent.futures import ThreadPoolExecutor

from ._connection import SumoConnection
from ._errors import *

"""

This file contains sketchy prototyping. NOT FOR PRODUCTION.

"""

class Sumo:
    """Main class to rule all classes. Or something."""

    def __init__(self, api=None):
        if api is None:
            _A = SumoConnection()
            self.api = _A.api
        else:
            self.api = api

    def __str__(self):
        return f'{self.__class__}'

    def find_ensembles(self, select='source,field', buckets='source', query=None, **kwargs):
        """Trigger search on Sumo, return EnsembleOnSumo instances"""

        if kwargs:
            for kwarg in kwargs:
                query += f'&${kwarg}'

        if query is None:
            query = '*'

        print(f'query: {query}')
        response = self.api.searchroot(query=query, select=select, buckets=buckets)

        hits = response.get('hits').get('hits')

        return [EnsembleOnSumo(hit.get('_id'), api=self.api) for hit in hits]

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
        self._fmu_ensemble_id = None
        self._files = []
        self._api = api
        self._sumo_parent_id = None
        self._on_sumo = None

    def __str__(self):
        s = f'{self.__class__}, {len(self._files)} files.'

        if self._sumo_parent_id is not None:
            s += f'\nInitialized on Sumo. Sumo_ID: {self._sumo_parent_id}'
        else:
            s += '\nNot initialized on Sumo.'

        s += '\nFMU casename: {}'.format(self.casename)

        return s

    def __repr__(self):
        return str(self.__str__)

    @property
    def on_sumo(self):
        if self._on_sumo is None:
            self.find_ensemble_on_sumo()
        return self._on_sumo            

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
    def sumo_parent_id(self):
        if self._sumo_parent_id is None:
            self._sumo_parent_id = self._get_sumo_parent_id()
        return self._sumo_parent_id

    @property
    def fmu_ensemble_id(self):
        if self._fmu_ensemble_id is None:
            self._fmu_ensemble_id = self._get_fmu_ensemble_id()
        return self._fmu_ensemble_id

    @property
    def files(self):
        return self._files

    def find_ensemble_on_sumo(self):
        """Call Sumo, search for this ensemble. Return True if found, and set self._sumo_parent_id.
        return False if not.

        Criteria for ensemble identified on Sumo: fmu_ensemble_id
        """

        ensembles_on_sumo = [e for e in EnsemblesOnSumo(api=self.api).ensembles]

        for ensemble_on_sumo in ensembles_on_sumo:
            if self.fmu_ensemble_id == ensemble_on_sumo.fmu_ensemble_id:
                print('Found it on Sumo')
                self.sumo_parent_id = ensemble_on_sumo.sumo_parent_id
                return True
            print('Not found on Sumo')
            return False


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

    def _get_sumo_parent_id(self):
        """Call sumo, check if the ensemble is already there. Use fmu_ensemble_id for this."""

        print('Getting SumoID')

        # search for all ensembles on Sumo, matching on fmu_ensemble_id
        E = EnsemblesOnSumo(api=self.api)
        matches = [m.sumo_parent_id for m in E.ensembles if m.fmu_ensemble_id == self.fmu_ensemble_id]

        print('fmu_ids on Sumo:')
        for _id in [e.fmu_ensemble_id for e in E.ensembles]:
            print(_id)

        print('this fmu_ensemble_id:')
        print(self.fmu_ensemble_id)

        if len(matches) == 0:
            print('No matching ensembles found on Sumo --> Not registered on Sumo')
            print('Registering ensemble on Sumo')
            sumo_parent_id = self._upload_manifest(self.manifest)
            print('Ensemble registered. SumoID: {}'.format(sumo_parent_id))
            return sumo_parent_id

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
        response = self.api.save_top_level_json(json=manifest)
        returned_object_id = response.text
        return returned_object_id

    def _load_manifest(self, manifest_path:str):
        """Given manifest path, load the yaml file, return dict"""

        if not os.path.isfile(manifest_path):
            raise IOError('File does not exist: {}'.format(manifest_path))

        with open(manifest_path, 'r') as stream:
            yaml_data = yaml.safe_load(stream)

        return yaml_data

    def _get_fmu_ensemble_id(self):
        """Look up and return ensemble_id from manifest"""
        fmu_ensemble_id = self.manifest.get('fmu_ensemble_id')
        return fmu_ensemble_id

    def upload(self, upload_files=True, threads=4):
        """Trigger upload of ensemble"""
        if self._sumo_parent_id is None:
            self._sumo_parent_id = self._get_sumo_parent_id()

        if upload_files:
            upload_response = UPLOAD_FILES(files=self.files, sumo_parent_id=self._sumo_parent_id, api=self.api, threads=threads)

        print(f'Uploaded {len(self.files)} in {upload_response.get("time_elapsed")} seconds')

class EnsemblesOnSumo:
    """Class for holding multiple ensembles on Sumo"""

    def __init__(self, api=None):

        """
        ensembles: List of EnsembleOnSumo instances
        """

        print('INIT EnsemblesOnSumo')

        if api is None:
            _A = SumoConnection()
            self.api = _A.api
        else:
            self.api = api

        self._ensembles = self.get_ensembles()

    @property
    def ensembles(self):
        return self._ensembles

    def get_ensembles(self):
        """Get list of ensembles from Sumo differentiated by their unique ID"""

        print('get_ensembles()')
        query = "*"
        select = 'source,field'
        buckets = 'source'
        search_results = self.api.searchroot(query, select=select, buckets=buckets)
        hits = search_results.get('hits', {}).get('hits')

        if hits is None:
            #raise IOError('Unexpected response from Sumo. "hits" was not included.')
            print('No hits - empty index?')
            return []

        if len(hits) == 0:
            print(f'No hits for query {query}')
            return []

        hit_ids = [h.get('_id') for h in hits]

        ensembles = [EnsembleOnSumo(sumo_parent_id=_id, api=self.api) for _id in hit_ids]

        return ensembles

class EnsembleOnSumo:
    """Class for holding an ensemble stored on Sumo"""

    def __init__(self, sumo_parent_id:str, api=None):
        """
        sumo_parent_id: The unique ID for the specific run assigned by Sumo

        Possible source of confusion: The ensemble_id is the one Sumo has assigned, not
        the one that was given from the source.
        """

        print('INIT EnsembleOnSumo. sumo_parent_id given: {}'.format(sumo_parent_id))

        self.sumo_parent_id = sumo_parent_id
        self._fmu_ensemble_id = None
        self._casename = None

        if api is None:
            _A = SumoConnection()
            self.api = _A.api
        else:
            self.api = api

        self._metadata = None
        self._data = None

    def __repr__(self):
        txt = f"""{self.__class__} ({self.casename})"""
        return str(txt)

    def describe(self):
        """Give a more extensive description of the ensemble"""
        txt = f"\n{self.__class__}"\
              f"\nsumo_parent_id: {self.sumo_parent_id}"\
              f"\nfmu_ensemble_id: {self.fmu_ensemble_id}"\
              f"\ncase: {self.casename}"\
              f"\nuser: {self.user}"\

        return str(txt)


    @property
    def metadata(self):
        if self._metadata is None:
            self._metadata = self._get_metadata()
        return self._metadata

    @property
    def manifest(self):
        return self.metadata.get('_source')

    @property
    def fmu_ensemble_id(self):
        return self.manifest.get('fmu_ensemble_id')

    @property
    def casename(self):
        return self.manifest.get('case')

    @property
    def user(self):
        return self.manifest.get('user')

    def delete(self):
        """Delete this ensemble from Sumo"""
        print(self.sumo_parent_id)
        print(type(self.sumo_parent_id))
        response = self.api.delete_object(self.sumo_parent_id)

        if response != 'ok':
            print('\n')
            print(response)
            raise DeleteFailed()

        return response

    def data(self):
        if self._data is None:
            self._data = self._get_data()
        return self._data

    def _get_metadata(self):
        """Get metadata for this ensemble"""
        data_from_sumo = self.api.get_json(object_id=self.sumo_parent_id)
        return data_from_sumo

    def _get_data(self):
        """Get children for this ensemble"""
        data_from_sumo = self.api.get_json()

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

    #def upload(self):
    #    """Trigger upload of all files"""
    #
    #    upload_respnse = UPLOAD_FILES(files=files, api=api)
    #    print(f'Uploaded {len(self.files)} in {upload_response.get('time_elapsed')} seconds')

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
        self._casename = None
        self._sumo_parent_id = None
        self._sumo_child_id = None
        self._sumo_child_id_blob = None
        self._filepath_relative_to_case_root = None
        self._basename = None
        self._dirname = None
        self._dtype = None
        self._fformat = None

        self._metadata['datetime'] = self._datetime_now()
        self._metadata['id'] = self._id_block()
        self._metadata['data']['relative_file_path'] = self.filepath_relative_to_case_root


    def __repr__(self):
        s =  f'\n# {self.__class__}'
        s += f'\n# Diskpath: {self.path}'
        s += f'\n# Basename: {self.basename}'
        s += f'\n# Casename: {self.casename}'
        s += f'\n# Relative path: {self.filepath_relative_to_case_root}'
        s += f'\n# Bytestring length: {len(self.bytestring)}'
        s += f'\n# Data type: {self.dtype}'
        s += f'\n# File format: {self.fformat}'

        if self.sumo_child_id is None:
            s += '\n# Not uploaded to Sumo'
        else:
            s += f'\n# Uploaded to Sumo. Sumo_ID: {self.sumo_child_id}'

        s += '\n\n'

        return s

    @property
    def sumo_parent_id(self):
        return self._sumo_parent_id

    @property
    def sumo_child_id(self):
        return self._sumo_child_id

    @property
    def filepath_relative_to_case_root(self):
        if self._filepath_relative_to_case_root is None:
            self._filepath_relative_to_case_root = self._get_filepath_relative_to_case_root()
        return self._filepath_relative_to_case_root

    @property
    def path(self):
        return self._path

    @property
    def casename(self):
        if self._casename is None:
            self._casename = self._get_casename()
        return self._casename

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

    def _id_block(self):
        """Create the id block to the metadata"""
        
        if self.dtype == 'surface':
            ids = ["data.relative_file_path", "fmu_ensemble_id"]
        elif self.dtype == 'polygons':
            ids = ["data.relative_file_path", "fmu_ensemble_id"]
        else:
            raise ValueError('Unknown data type: {}'.format(type))

        return ids

    def _datetime_now(self):
        """Return datetime now on FMU standard format"""
        return datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    def _get_filepath_relative_to_case_root(self):
        """Derive the local filepath from the absolute path"""
        casename = self.metadata.get('case')
        if casename not in self.path:
            raise IOError('Could not find casename in filepath')
        return self.path.split(casename)[-1][1:]

    def _get_casename(self):
        """Look up casename from metadata"""
        casename = self.metadata.get('case')
        if not casename:
            raise MetadataError('Could not get casename from metadata')
        return casename

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

    def _upload_metadata(self, api, sumo_parent_id):
        response = api.save_child_level_json(json=self.metadata, object_id=sumo_parent_id)
        return response

    def _upload_bytestring(self, api):
        response = api.save_blob(object_id=self.sumo_child_id, blob=self.bytestring)
        return response

    def upload_to_sumo(self, sumo_parent_id, api=None):
        """Upload this file to Sumo"""

        # what if sumo_parent_id does not exist on Sumo?

        response = {}

        if not sumo_parent_id:
            return {'status': 'failed', 'response': 'Failed, sumo_parent_id passed to upload_to_sumo: {}'.format(sumo_parent_id)}

        # TODO: Do a check towards Sumo for confirming that ID is referring to existing ensemble

        #print(f'  Uploading {self.filepath_relative_to_case_root}')
        #print('  > metadata')
        response = self._upload_metadata(api=api, sumo_parent_id=sumo_parent_id)
        if not response.ok:
            return {'status': 'failed', 'response': response}
        self._sumo_child_id = response.text

        response = self._upload_bytestring(api=api)
        if not response.ok:
            return {'status': 'failed', 'response': response}
        self._sumo_child_id_blob = response.text

        return {'status': 'ok', 'response': response.text}


def UPLOAD_FILES(files:list, sumo_parent_id:str, api=None, threads=4):
    """
    Upload files, including JSON, to specified ensemble

    files: list of FileOnDisk objects
    sumo_parent_id: sumo_parent_id for the parent ensemble

    Upload is kept outside classes to ease multithreading.
    """

    def _upload_files(files, api, sumo_parent_id, threads=4):
        with ThreadPoolExecutor(threads) as executor:
            files_and_responses = executor.map(_upload_file, [(file, api, sumo_parent_id) for file in files])
        return files_and_responses

    def _upload_file(arg):
        file, api, sumo_parent_id = arg
        file_and_response = (file, file.upload_to_sumo(api=api, sumo_parent_id=sumo_parent_id))
        return file_and_response

    _t0 = time.perf_counter()

    print(f'UPLOADING {len(files)} files with {threads} threads.')

    # first attempt
    files_and_responses = _upload_files(files=files, api=api, sumo_parent_id=sumo_parent_id, threads=threads)
    failed_uploads = [(file, response) for file, response in files_and_responses if response.get('status') != 'ok']

    if not failed_uploads:
        _t1 = time.perf_counter()
        _dt = _t1-_t0

        print('\n==== UPLOAD DONE ====')
        return {'elements' : [s.basename for s in files],
                'sumo_parent_id' : sumo_parent_id,
                'count' : len(files),
                'time_start' : _t0,
                'time_end' : _t1,
                'time_elapsed' : _dt,}

    if len(failed_uploads) == len(files):
        print('\nALL FILES FAILED')
    else:
        print('\nSome uploads failed:')

    for file, response in failed_uploads:
        print(f'{file.filepath_relative_to_case_root}: {response}')

    print('\nRetrying {} failed uploads:'.format(len(failed_uploads)))
    failed_files = [file for file, response in failed_uploads]
    files_and_responses = _upload_files(files=failed_files, api=api, sumo_parent_id=sumo_parent_id, threads=threads)
    failed_uploads = [(file, response) for file, response in files_and_responses if response.get('status') != 'ok']

    if failed_uploads:
        print('Uploads still failed after second attempt:')
        for failed in failed_uploads:
            print(failed)

    _t1 = time.perf_counter()
    _dt = _t1-_t0

    return {'elements': [s.basename for s in files],
            'sumo_parent_id': sumo_parent_id,
            'count': len(files),
            'time_start': _t0,
            'time_end': _t1,
            'time_elapsed': _dt,
            'failed': len(failed_uploads)}


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