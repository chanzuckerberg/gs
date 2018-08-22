SHELL=/bin/bash

test: lint install
	coverage run --source=gs -m unittest discover -v -t . -s test

lint:
	./setup.py flake8

version: gs/version.py

gs/version.py: setup.py
	echo "__version__ = '$$(python setup.py --version)'" > $@

build: version
	-rm -rf dist
	python setup.py bdist_wheel

install: clean build
	pip install --upgrade dist/*.whl

init_docs:
	cd docs; sphinx-quickstart

docs:
	$(MAKE) -C docs html

clean:
	-rm -rf build dist
	-rm -rf *.egg-info

.PHONY: test lint install release docs clean

include common.mk
