#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup, find_packages

setup(
    name="pysr_service",
    version="1.0.0",
    description="PySR (Python Symbolic Regression) as a Service",
    author="Your Name",
    author_email="your.email@example.com",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "pysr",
        "numpy",
        "pandas",
        "matplotlib",
        "fastapi",
        "uvicorn",
        "python-multipart",
    ],
    entry_points={
        "console_scripts": [
            "pysr-service=main:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Science/Research",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
    ],
    python_requires=">=3.7",
) 