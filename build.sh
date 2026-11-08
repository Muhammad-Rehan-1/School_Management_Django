#!/usr/wbin/env bash
# Exit on error
set -o errexit

# Install python packages
pip install -r requirements.txt

# Collect static files
python manage.py collectstatic --no-input

# update