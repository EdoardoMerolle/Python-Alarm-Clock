#!/bin/bash

# 1. Force the script to stop if any command fails
set -e

echo "--- STARTING SMART DISPLAY ---"

# 2. Move to the folder where this script lives
# This ensures we are inside /home/pi/SmartDisplay/
cd "$(dirname "$0")"
echo "Working Directory: $(pwd)"

# 3. Find and Activate the Virtual Environment
echo "Looking for virtual environment..."

if [ -f "../.venv/bin/activate" ]; then
    echo "Found .venv in parent folder. Activating..."
    source ../.venv/bin/activate
elif [ -f ".venv/bin/activate" ]; then
    echo "Found .venv in current folder. Activating..."
    source .venv/bin/activate
else
    echo "ERROR: Could not find .venv/bin/activate in either:"
    echo "  - $(pwd)/.venv"
    echo "  - $(dirname $(pwd))/.venv"
    echo "Please make sure your virtual environment is created."
    read -p "Press Enter to exit..."
    exit 1
fi

# 4. Run the Python App
echo "Starting main.py..."
if [ -f "main.py" ]; then
    python main.py
else
    echo "ERROR: main.py not found in $(pwd)"
fi

# 5. Keep window open if app crashes
echo "--------------------------------"
echo "App closed. Press Enter to exit."
read -p ""