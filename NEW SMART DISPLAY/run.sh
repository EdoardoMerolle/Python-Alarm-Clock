#!/bin/bash

# 1. Navigate to the directory where this script is located
# This ensures the app finds 'assets/' correctly no matter where you run the script from.
cd "$(dirname "$0")"

# 2. Check if the .venv directory exists
if [ -d ".venv" ]; then
    # Activate the virtual environment
    source .venv/bin/activate
else
    echo "Error: .venv directory not found."
    exit 1
fi

# 3. Run the application
cd SmartDisplay
python main.py
