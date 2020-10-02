#!/bin/bash


BASE_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd ${BASE_DIR}/src

env_python=$(pipenv --venv)/bin/python
sudo $env_python gateway.py

