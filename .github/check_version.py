"""Fail before building if the version cannot be published.

Two ways a release goes wrong late: the version was never bumped, so PyPI
rejects the upload as a duplicate after the build has already run; or the git
tag says one thing and fireeye/__init__.py says another, so the wrong number
ships under the right tag.
"""

import json
import os
import pathlib
import sys
import urllib.error
import urllib.request

PROJECT = "FireEye-AWS"


def package_version():
    init = pathlib.Path(__file__).resolve().parents[1] / "fireeye" / "__init__.py"
    for line in init.read_text().splitlines():
        if line.startswith("__version__"):
            return line.split('"')[1]

    sys.exit("no __version__ in fireeye/__init__.py")


def published_versions():
    url = f"https://pypi.org/pypi/{PROJECT}/json"
    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            return set(json.load(r)["releases"])
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return set()  # nothing published yet
        raise


version = package_version()
tag = os.environ.get("RELEASE_TAG", "")

if tag and tag.lstrip("v") != version:
    sys.exit(f"tag {tag} does not match fireeye.__version__ {version}")

if version in published_versions():
    sys.exit(
        f"{PROJECT} {version} is already on PyPI. Bump __version__ in "
        f"fireeye/__init__.py; PyPI never accepts a version twice."
    )

print(f"{version} is not on PyPI yet" + (f" and matches tag {tag}" if tag else ""))
