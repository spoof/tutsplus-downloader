#!/usr/bin/env python
# -*- coding: utf-8 -*-
try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

# Dirty hack to prevent ``python setup.py sdist`` from making hard links:
# it doesn't work in VMWare/VBox shared folders.
import os
del os.link

install_requires = [
    'requests',
    'pyquery',
    'clint',
    'progressbar',
]

setup(
    name='tutsplus-downloader',
    version='1.0',
    license='BSD',
    description='Course downloader for TutsPlus',
    author='Sergey Safonov',
    author_email='spoof@spoofa.info',
    url='https://github.com/spoof/tutsplus-downloader',
    long_description=__doc__,
    classifiers=[
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: Unix',
        'Programming Language :: Python',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
    ],
    install_requires=install_requires,
    include_package_data=True,
    zip_safe=False,
    platforms='any',
    py_modules=['tutsplus_downloader'],
    entry_points={
        'console_scripts': [
            'tutsplus-downloader = tutsplus_downloader:main',
        ],
    },
)
