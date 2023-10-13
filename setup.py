#!/usr/bin/env python

"""The setup script."""

from setuptools import setup, find_packages

with open("README.rst") as readme_file:
    readme = readme_file.read()

with open("HISTORY.rst") as history_file:
    history = history_file.read()

requirements = [
    "Click>=7.0",
]

test_requirements = [
    "pytest>=3",
]

setup(
    author="Nic Mostert",
    author_email="nicolas.mostert@horizons.govt.nz",
    python_requires=">=3.6",
    classifiers=[
        "Development Status :: 2 - Pre-Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Natural Language :: English",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
    ],
    description="Python Package providing a suite of processing tools and utilities for Hilltop hydrological data.",
    entry_points={
        "console_scripts": [
            "hydro_processing_tools=hydro_processing_tools.cli:main",
        ],
    },
    install_requires=requirements,
    license="GNU General Public License v3",
    long_description=readme + "\n\n" + history,
    include_package_data=True,
    keywords="hydro_processing_tools",
    name="hydro_processing_tools",
    packages=find_packages(
        include=["hydro_processing_tools", "hydro_processing_tools.*"]
    ),
    test_suite="tests",
    tests_require=test_requirements,
    url="https://github.com/nicmostert/hydro_processing_tools",
    version="0.1.0",
    zip_safe=False,
)
