from setuptools import setup, find_packages
import glob

with open('requirements.txt') as f:
    required = f.read().splitlines()

with open("README.md", "r") as fh:
    long_description = fh.read()

print(find_packages())
# scripts
scripts = glob.glob("./helperRoutines/*py")
print(scripts)

setup(
    name="(A)Synchronous TCP MODBUS Client",
    version="5.3.2",
    author="Ralf A. Timmermann",
    install_requires=required,
    author_email="rtimmermann@astro.uni-bonn.de",
    description="MODBUS Sync/Async Clients + Helper Functions",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/ccatp/MODBUS",
    packages=["modbusClientSync", "modbusClientAsync"],
    scripts=scripts,
    python_requires='>=3.10'
)
