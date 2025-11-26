#!/bin/bash
# Run tests inside virtualenv
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -r requirements.txt
pytest -q
