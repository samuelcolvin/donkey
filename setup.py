from pathlib import Path

from importlib.machinery import SourceFileLoader
from setuptools import setup

with Path(__file__).parent.joinpath('README.rst').open() as f:
    long_description = f.read()

# avoid loading the package before requirements are installed:
version = SourceFileLoader('version', 'donkey/version.py').load_module()

setup(
    name='donkey-make',
    version=str(version.VERSION),
    description='Like make but for the 21st century.',
    long_description=long_description,
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: Console',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Intended Audience :: Developers',
        'Intended Audience :: Information Technology',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: MIT License',
        'Operating System :: Unix',
        'Operating System :: POSIX :: Linux',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: System :: Systems Administration',
    ],
    author='Samuel Colvin',
    author_email='s@muelcolvin.com',
    url='https://github.com/samuelcolvin/donkey',
    license='MIT',
    packages=['donkey'],
    zip_safe=True,
    entry_points="""
        [console_scripts]
        donkey=donkey.cli:cli
        donk=donkey.cli:cli
    """,
    install_requires=[
        'click>=6.6',
        'PyYAML>=3.12',
        'trafaret>=0.7.5',
        'trafaret-config>=0.1.1',
        'watchdog>=0.8.3',
    ],
)
