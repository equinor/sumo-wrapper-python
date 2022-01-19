# -*- coding: utf-8 -*-

from setuptools import setup, find_packages

setup(
    name='sumo-wrapper-python',
    description='Python wrapper for the Sumo API',
    url='https://github.com/equinor/sumo-wrapper-python',
    keywords='sumo, python',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Natural Language :: English',
        'Programming Language :: Python :: 3.7'
        'Programming Language :: Python :: 3.8'
        ],
    version='0.1.4',
    author='Equinor ASA',
    install_requires=[
                    'requests',
                    'msal',
                    'PyYAML',
                    'setuptools'
                    ],
    python_requires=">=3.4",
    packages=find_packages("src"),
    package_dir={"": "src"},
    include_package_data=True,
    zip_safe=False,
    entry_points={
        "console_scripts": ["sumo_login = sumo.wrapper.login:main"]
        }
)
