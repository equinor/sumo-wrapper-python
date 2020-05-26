"""Classes for error handling"""

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