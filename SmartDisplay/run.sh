#!/bin/bash
set -euo pipefail

# Resolve assets, QML, and the database relative to this script.
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"

if [[ ! -x .venv/bin/python ]]; then
    echo "Error: .venv is missing. Create it and install requirements.txt first." >&2
    exit 1
fi

# Use the project's interpreter regardless of the caller's active environment.
exec .venv/bin/python main.py "$@"
