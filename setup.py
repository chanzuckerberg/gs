#!/usr/bin/env python

import os, sys
from setuptools import setup, find_packages

install_requires = [line.rstrip() for line in open(os.path.join(os.path.dirname(__file__), "requirements.txt"))]
tests_require = ["coverage", "flake8", "wheel"]

setup(
    name='gs',
    version='0.5.5',
    url='https://github.com/kislyuk/gs',
    license='MIT License',
    author='Andrey Kislyuk',
    author_email='kislyuk@gmail.com',
    description='A minimalistic Google Storage client',
    long_description=open('README.rst').read(),
    install_requires=install_requires,
    tests_require=tests_require,
    extras_require={
        ':python_version == "2.7"': ['futures']
    },
    packages=find_packages(exclude=['test']),
    entry_points={
        'console_scripts': [
            'gs=gs.cli:cli'
        ],
    },
    platforms=['MacOS X', 'Posix'],
    include_package_data=True,
    test_suite='test',
    classifiers=[
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: MacOS :: MacOS X',
        'Operating System :: POSIX',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Topic :: Software Development :: Libraries :: Python Modules'
    ]
)
