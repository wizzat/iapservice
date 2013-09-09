#!/bin/bash
export IAP_SERVICE_CONFIG=config
export PYTHONPATH=$PWD

find . -name '*pyc' | xargs rm -f
dropdb iapservice
createdb iapservice

python iapservice/model.py
python -m unittest discover -fv . "test_*$1*.py"
