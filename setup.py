import glob
import os

from setuptools import find_packages, setup

with open("requirements.txt") as f:
    required = f.read().splitlines()

with open("README.md", "r") as fh:
    long_description = fh.read()


setup(
    name="MODBUS",  # Replace with your username
    version="1.0.0",
    author="<authorname>",
    install_requires=required,
    author_email="<authorname@templatepackage.com>",
    description="<Template Setup.py package>",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/ccatp/MODBUS",
    packages=find_packages(),
    python_requires=">=3.6",
    entry_points={
        "console_scripts": [
            "mb_client=modbus.modbus_cli:modbus",
            "mb_client_rest_api=modbus.mb_client_RestAPISync:main",
        ]
    },
)
