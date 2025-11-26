#!/bin/bash
set -e
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
echo "Setup complete. Activate environment: source .venv/bin/activate"
