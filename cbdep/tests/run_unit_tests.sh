#!/bin/bash
[ ! -d venv ] && python3 -m venv env
source env/bin/activate
pip3 install -r ../../requirements.txt
pip3 install pytest pytest-cov
coverage run --source=cbdep.cbdep.scripts --module pytest --verbose . && coverage report --show-missing
deactivate