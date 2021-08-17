#!/usr/bin/env python3

from setuptools import setup
from subprocess import check_output

version = check_output(["git", "describe", "--tags", "--always"])[:-1].decode()


setup(
	name="tango-rpialarm",
	version=version,
	description="Tango Device Server for RaspberryPi GPIO alarm",
	author="Grzegorz Kowalski (daneos)",
	author_email="daneos@daneos.com",
	url="https://github.com/daneos/tango-rpialarm",
	license="GPLv3",
	scripts=["rpialarm"],
	packages=["tango_rpialarm"],
	package_dir={"tango_rpialarm": "."}
)
