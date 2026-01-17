#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"

# Use venv python if present
if [ -x ".venv/bin/python" ]; then
  PYTHON=".venv/bin/python"
else
  PYTHON="python3"
fi

export PYTHONPATH="src"
$PYTHON src/clock/app.py
