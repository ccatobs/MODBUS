import os
from setuptools import setup,find_packages
import glob

with open('requirements.txt') as f:
    required = f.read().splitlines()

with open("README.md", "r") as fh:
    long_description = fh.read()

print(find_packages())
# scripts
scripts = glob.glob("./helperRoutinesSync/*py")
scripts.extend(glob.glob("./helperRoutinesAsync/*py"))
print(scripts)

setup(

    name="MODBUS", # Replace with your username
    version="1.0.0",
    author="<authorname>",
    install_requires=required,
    author_email="<authorname@templatepackage.com>",
    description="<Template Setup.py package>",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/ccatp/MODBUS",
    packages=["modbusClientSync","modbusClientAsync"],
    scripts=scripts,
    python_requires='>=3.6',
)


