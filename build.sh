#!/usr/bin/env bash
set -o errexit

# 1. Python packages install karein
pip install -r requirements.txt

# 2. Static files collect karein
python manage.py collectstatic --no-input