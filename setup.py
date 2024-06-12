#!/usr/bin/env python

import setuptools
from distutils.core import setup, Extension

setup(name='nuget-s3',
    version='1.0',
    packages=[
        'nuget_s3',
    ],
    scripts = [
    ],
    install_requires='zappa>=0.44.3 boto3 six flask markupsafe==2.0.1'.split(),
)
