#!/bin/bash
export IAP_SERVICE_CONFIG=$PWD/config
export PYTHONPATH=$PWD:$PYTHONPATH

find . -name '*pyc' | xargs rm -f
dropdb iapservice
createdb iapservice

python iapservice/model.py
cd tests && python -m unittest discover -fv . "test*$1*.py"
