#!/usr/bin/env python
from setuptools import setup


setup(
    name="pythermiagenesis",
    version="0.1.3",
    author="Johan Isaksson",
    author_email="johan@generatorhallen.se",
    description="Python wrapper for getting data from Thermia Mega and Inverter heat pumps \
        via Modbus TCP.",
    include_package_data=True,
    url="https://github.com/cjne/pythermiagenesis",
    license="MIT",
    packages=["pythermiagenesis"],
    python_requires=">=3.6",
    install_requires=["pymodbustcp"],
    classifiers=[
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python",
        "Operating System :: OS Independent",
    ],
    setup_requires=("pytest-runner"),
    tests_require=(
        "asynctest",
        "pytest-cov",
        "pytest-asyncio",
        "pytest-trio",
        "pytest-tornasync",
    ),
)
