#!/bin/bash -ex

# We need to do this before launching pytest, so it can't be part of the
# test itself. This is to make sure that CBD-4352 is fixed.
unset LANG

[ ! -d env ] && python3 -m venv env
source env/bin/activate
pip3 install \
    pytest \
    pytest-cov \
    wheel
pip3 install -r ../../requirements.txt

coverage run --source=. --module pytest -k "${TESTS-test}" --verbose . && coverage report --show-missing
deactivate
