from __future__ import annotations
import os, sys, subprocess
from pathlib import Path

root = Path(__file__).resolve().parent
os.chdir(root)

# Set PYTHONPATH=src
os.environ["PYTHONPATH"] = str(root / "src")

# Prefer venv python if present, else current interpreter
venv_py = root / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
py = str(venv_py) if venv_py.exists() else sys.executable

app = root / "src" / "clock" / "app.py"
raise SystemExit(subprocess.call([py, str(app)]))
