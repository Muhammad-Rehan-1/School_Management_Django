#!/usr/bin/env bash
set -o errexit

# 1. System dependencies aur Microsoft ODBC Driver 17 install karein
apt-get update
apt-get install -y curl gnupg apt-transport-https
curl -fsSL https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor -o /usr/share/keyrings/microsoft-prod.gpg
curl -fsSL https://packages.microsoft.com/config/ubuntu/22.04/prod.list | tee /etc/apt/sources.list.d/mssql-release.list

apt-get update
ACCEPT_EULA=Y apt-get install -y msodbcsql17 unixodbc-dev

# 2. Python packages install karein
pip install -r requirements.txt

# 3. Static files collect kareins
python manage.py collectstatic --no-input