#!/bin/bash
# Verbose test run generating JUnit XML and HTML report using venv
# Usage: run_test_verbose.sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install pytest-html
pytest -vv --junitxml=pytest-report.xml --html=pytest-report.html --self-contained-html --tb=short
