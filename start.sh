#!/usr/bin/env bash
# Starts the portal on macOS or Linux. Windows users: start_portal.cmd
set -e
cd "$(dirname "$0")"

if [ ! -x ".venv/bin/python" ]; then
  echo "No virtual environment yet - running setup first."
  python3 setup.py
fi

echo "Starting InternRadar on http://127.0.0.1:8700"
exec .venv/bin/python app.py
