# -*- coding: utf-8 -*-

import pathlib
from urllib.parse import urlparse
from pip._internal.req import parse_requirements as parse
from setuptools import find_packages, setup


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
REQUIREMENTS_TEST = parse_requirements("requirements/requirements_test.txt")

EXTRAS_REQUIRE = {"docs": REQUIREMENTS_DOCS, "test": REQUIREMENTS_TEST}


setup(
    name="sumo-wrapper-python",
    description="Python wrapper for the Sumo API",
    long_description=pathlib.Path("README.md").read_text(),
    long_description_content_type="text/markdown",
    license="Apache 2.0",
    url="https://github.com/equinor/sumo-wrapper-python",
    keywords="sumo, python",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Natural Language :: English",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    use_scm_version={"write_to": "src/sumo/wrapper/version.py"},
    author="Equinor ASA",
    install_requires=REQUIREMENTS,
    python_requires=">=3.8",
    packages=find_packages("src"),
    package_dir={"": "src"},
    include_package_data=True,
    zip_safe=False,
    extras_require=EXTRAS_REQUIRE,
    entry_points={"console_scripts": ["sumo_login = sumo.wrapper.login:main"]},
)
