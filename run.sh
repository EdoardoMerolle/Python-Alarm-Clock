#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"

# Create venv if missing
if [ ! -x ".venv/bin/python" ]; then
  echo "Creating venv in .venv..."
  python3 -m venv .venv
fi

# Activate venv
source .venv/bin/activate

# Ensure pip tooling
python -m pip install --upgrade pip wheel setuptools

# Install deps (prefer requirements.txt)
if [ -f "requirements.txt" ]; then
  python -m pip install -r requirements.txt
else
  python -m pip install kivy
fi

export PYTHONPATH="src"
python src/clock/app.py
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
