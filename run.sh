#!/usr/bin/env bash

set -a
source config.env
source .venv/bin/activate
set +a

pip install -r requirements.txt

python3 main.py