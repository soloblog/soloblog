#!/bin/sh
set -eu

# Cloudron names the app's address; a domain changed there restarts the
# app with the new one, so Settings' own address field isn't needed
export BASE_URL="${CLOUDRON_APP_ORIGIN}"

# starts as root, hands /app/data to its own user and runs as that user
cd /app
exec python app.py
