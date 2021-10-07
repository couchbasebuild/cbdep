#!/bin/bash

# We need to do this before launching pytest, so it can't be part of the
# test itself. This is to make sure that CBD-4352 is fixed.
unset LANG

[ ! -d venv ] && python3 -m venv env
source env/bin/activate
pip3 install -r ../../requirements.txt
pip3 install pytest pytest-cov
coverage run --source=cbdep.cbdep.scripts --module pytest -k "${TESTS-test}" --verbose . && coverage report --show-missing
deactivate
