#!/usr/bin/env python

from os import path, walk

import sys
from setuptools import setup, find_packages

NAME = "orange3-scoring"

VERSION = "0.0.1"

DESCRIPTION = "Add-on containing scoring engine widgets for PFA, PMML and ONNX (coming soon) models"
LONG_DESCRIPTION = open(path.join(path.dirname(__file__), 'README.md')).read()

LICENSE = "MIT"

KEYWORDS = [
    # [PyPi](https://pypi.python.org) packages with keyword "orange3 add-on"
    # can be installed using the Orange Add-on Manager
    'orange3 add-on',
    'scoring',
    'inference',
    'pfa',
    'pmml',
    'onnx',
]

PACKAGES = find_packages()

PACKAGE_DATA = {
    'orangecontrib.scoring': ['tutorials/*.ows', 'tests/*.json', 'tests/*.xml'],
    'orangecontrib.scoring.widgets': ['icons/*'],
}

DATA_FILES = [
    # Data files that will be installed outside site-packages folder
]

INSTALL_REQUIRES = [
    'Orange3',
    'titus2',
    'pypmml',
]

ENTRY_POINTS = {
    # Entry points that marks this package as an orange add-on. If set, addon will
    # be shown in the add-ons manager even if not published on PyPi.
    'orange3.addon': (
        'scoring = orangecontrib.scoring',
    ),
    # Entry point used to specify packages containing tutorials accessible
    # from welcome screen. Tutorials are saved Orange Workflows (.ows files).
    'orange.widgets.tutorials': (
        # Syntax: any_text = path.to.package.containing.tutorials
        'scoringtutorials = orangecontrib.scoring.tutorials',
    ),

    # Entry point used to specify packages containing widgets.
    'orange.widgets': (
        # Syntax: category name = path.to.package.containing.widgets
        # Widget category specification can be seen in
        #    orangecontrib/example/widgets/__init__.py
        'Scoring = orangecontrib.scoring.widgets',
    ),

    # Register widget help
    "orange.canvas.help": (
        'html-index = orangecontrib.scoring.widgets:WIDGET_HELP_PATH',)
}

NAMESPACE_PACKAGES = ["orangecontrib"]

TEST_SUITE = "orangecontrib.scoring.tests.suite"


def include_documentation(local_dir, install_dir):
    global DATA_FILES
    if 'bdist_wheel' in sys.argv and not path.exists(local_dir):
        print("Directory '{}' does not exist. "
              "Please build documentation before running bdist_wheel."
              .format(path.abspath(local_dir)))
        sys.exit(0)

    doc_files = []
    for dirpath, dirs, files in walk(local_dir):
        doc_files.append((dirpath.replace(local_dir, install_dir),
                          [path.join(dirpath, f) for f in files]))
    DATA_FILES.extend(doc_files)

if __name__ == '__main__':
    #include_documentation('doc/build/html', 'help/orange3-scoring')
    setup(
        name=NAME,
        version=VERSION,
        author="Ankit Mahato",
        author_email="ankmahato@gmail.com",        
        keywords=KEYWORDS,
        description=DESCRIPTION,
        long_description=LONG_DESCRIPTION,
        long_description_content_type="text/markdown",   
        url="https://github.com/animator/orange3-scoring",     
        license=LICENSE,
        packages=PACKAGES,
        package_data=PACKAGE_DATA,
        data_files=DATA_FILES,
        install_requires=INSTALL_REQUIRES,
        python_requires='>=3.5',
        entry_points=ENTRY_POINTS,
        namespace_packages=NAMESPACE_PACKAGES,
        test_suite=TEST_SUITE,
        include_package_data=True,
        zip_safe=False,
        classifiers=[  
            'Development Status :: 3 - Alpha', 
            'Intended Audience :: Developers',
            'Intended Audience :: Education',
            'Intended Audience :: Information Technology',
            'Intended Audience :: Science/Research',
            'Topic :: Scientific/Engineering',
            'Topic :: Scientific/Engineering :: Artificial Intelligence',
            'Topic :: Software Development',
            'Topic :: Software Development :: Libraries',
            'Topic :: Software Development :: Libraries :: Python Modules',
            'License :: OSI Approved :: MIT License',
            'Programming Language :: Python :: 3 :: Only',
            'Programming Language :: Python :: 3',
            'Programming Language :: Python :: 3.5',
            'Programming Language :: Python :: 3.6',
            'Programming Language :: Python :: 3.7',
            'Programming Language :: Python :: 3.8',
            'Natural Language :: English',
        ],        
    )
