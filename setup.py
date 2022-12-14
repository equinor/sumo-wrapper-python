# -*- coding: utf-8 -*-

from setuptools import setup, find_packages
from pip._internal.req import parse_requirements as parse
from urllib.parse import urlparse


def _format_requirement(req):
    print(req)
    if req.is_editable:
        # parse out egg=... fragment from VCS URL
        parsed = urlparse(req.requirement)
        egg_name = parsed.fragment.partition("egg=")[-1]
        without_fragment = parsed._replace(fragment="").geturl()
        return f"{egg_name} @ {without_fragment}"
    return req.requirement


def parse_requirements(fname):
    """Turn requirements.txt into a list"""
    reqs = parse(fname, session="test")
    return [_format_requirement(ir) for ir in reqs]


REQUIREMENTS = parse_requirements("requirements/requirements.txt")
REQUIREMENTS_DOCS = parse_requirements("requirements/requirements_docs.txt")

EXTRAS_REQUIRE = {"docs": REQUIREMENTS_DOCS}


setup(
    name="sumo-wrapper-python",
    description="Python wrapper for the Sumo API",
    license="Apache 2.0",
    url="https://github.com/equinor/sumo-wrapper-python",
    keywords="sumo, python",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Natural Language :: English",
        "Programming Language :: Python :: 3.7" "Programming Language :: Python :: 3.8",
    ],
    use_scm_version={"write_to": "src/sumo/wrapper/version.py"},
    author="Equinor ASA",
    install_requires=REQUIREMENTS,
    python_requires=">=3.6",
    packages=find_packages("src"),
    package_dir={"": "src"},
    include_package_data=True,
    zip_safe=False,
    extras_require=EXTRAS_REQUIRE,
    entry_points={"console_scripts": ["sumo_login = sumo.wrapper.login:main"]},
)
