import os
import sys

from setuptools import find_packages
from setuptools import setup

# Utility function to read the README file.
# Used for the long_description.  It's nice, because now 1) we have a top level
# README file and 2) it's easier to type in the README file than to put a raw
# string in below ...
this_dir = os.path.dirname(__file__)
sys.path.append(this_dir)


def read(fname):
    return open(os.path.join(this_dir, fname)).read()


install_requires = ["boto3==1.35.54", "botocore==1.35.54", "jmespath==1.0.1", "python-dateutil==2.9.0.post0",
                    "s3transfer==0.10.3", "six==1.16.0", "urllib3==2.2.3"]

setup(
    name="FireEye",
    version="0.0.4",
    author="Hardik Nanda",
    author_email="hnanda21@gmail.com",
    description="Query cloudwatch logs insights for any AWS Resource",
    license="BSD",
    keywords="aws cloudwatch logs logs-insights",
    # url = "http://packages.python.org/an_example_pypi_project",
    # packages=['an_example_pypi_project', 'tests'],
    long_description=read('README.md'),
    long_description_content_type="text/markdown",
    packages=find_packages(
        where="fireeye",
    ),
    classifiers=[
        "Environment :: Console",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python :: 3.11",
        "Development Status :: 1 - Planning",
        "Topic :: Software Development",
        "License :: OSI Approved :: BSD License",
    ],
    install_requires=install_requires,
    python_requires=">=3.8",
    scripts=['fireeye/check_main.py'],
)
