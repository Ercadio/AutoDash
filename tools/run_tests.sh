#!/bin/bash

BASEDIR=$(dirname "$0")
export PYTHONPATH="${PYTHONPATH}:${BASEDIR}/../src"
python3.8 -m unittest discover -s "${BASEDIR}/../test"
