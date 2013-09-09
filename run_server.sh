#!/bin/bash
export IAP_SERVICE_CONFIG=config
export PYTHONPATH=$PWD

python iapservice/model.py
python iapservice/server.py
