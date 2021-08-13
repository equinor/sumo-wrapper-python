# sumo-wrapper-python
Development of Python wrappers for Sumo APIs


## Install by running: 
    
    pip install git+ssh://git@github.com/equinor/sumo-wrapper-python.git@master
    
## Example code:
[test_call_sumo_surface_api](scripts/examples/test_call_sumo_surface_api.py)

## Making it available in Komodo (Bleeding)
The wrapper and the uploader (https://github.com/equinor/fmu-sumo) are intended to be used by the Equinor community to upload, search, and delete data to/from SUMO. To make them accessable for our community, they should be available as a komodo distribution (https://github.com/equinor/komodo-releases).

In order to do so, we should follow these steps:

### 1) Clone the Komodo repository and, from the master branch, create a new feature branch
https://github.com/equinor/komodo-releases

### 2) Edit the file package_status.yml and add/modify the package information
For Example: 
    sumo-wrapper-python:
        visibility: public
        maturity: experimental
        importance: low
        
The package name must correspond to the name of the package's repository.

### 3) Edit the file repository.yml and add/modify the package information
Example:
    sumo-wrapper-python:
        v0.1.0:
            source: https://0c0b51dd4ca3c035c04c01dd74216c2ec6c1648b@github.com/equinor/sumo-wrapper-python.git
            fetch: git
            make: sh
            makefile: setup-py.sh
            maintainer: rgarc
            depends:
                - PyYAML
                - msal
                - requests
                - python
                - setuptools

Again, the package name must correspond to the repository's name. 

The second line corresponds to the current release tag for the package.

The source is the link for the repo + the PAT belonging to a bot user we set so we don't need to publish our own authentication (https://github.com/sumo-machine-user)

On the depends item, you should add the dependencies that must be installed in order to run the package. Note that dependecies already included in the standard library (e.g., the math library) don't need to be mentioned.

### 4) Edit the releases/matrices/bleeding.yml file and add/modify the package information
Example:
    sumo-wrapper-python: v0.1.0

In this file, you only need to add the repository's name and the current release tag. Note that this is for bleeding distribution (unstable). For adding to a more stable distribution, this edit should go to another file in this folder (but that would probably require input from the komodo team).

### 5) Create a Pull Request
Once you finish the edits, just push your branch with the changes and create a PR. The komodo team will then review it and merge it or give some feedback (you don't need to add reviewers nor merge with the master branch yourself).

For more information, you should contact the komodo team on the komodo/komodo-maintainers channel on Slack.
