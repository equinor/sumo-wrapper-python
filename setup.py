from setuptools import setup

setup(
    name='sumo_surface',
    url='https://github.com/equinor/sumo-surface-python',
    version='0.1',
    author='Lindvar Lagran',
    author_email='llag@equinor.com',
    install_requires=[
                    'adal',
                    'xtgeo',
                    ],
    packages=['sumo_surface_python']
)