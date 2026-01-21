@echo off
setlocal
cd /d %~dp0

REM Use venv python if present
if exist ".venv\Scripts\python.exe" (
  set "PYTHON=.venv\Scripts\python.exe"
) else (
  set "PYTHON=python"
)

set "PYTHONPATH=src"
"%PYTHON%" src\clock\app.py

endlocal
