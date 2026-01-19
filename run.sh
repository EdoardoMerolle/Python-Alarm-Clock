#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"

if [ -x ".venv/bin/python" ]; then
  PYTHON=".venv/bin/python"
else
  PYTHON="python3"
fi

export PYTHONPATH="src"
# exec git pull
exec "$PYTHON" src/clock/app.py

