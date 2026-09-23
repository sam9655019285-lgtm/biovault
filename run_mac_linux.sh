#!/usr/bin/env bash
# BioVault startup script for macOS/Linux.
# Run with:  bash run_mac_linux.sh
# Safe to run multiple times.

set -e

echo "============================================"
echo " BioVault - DNA Digital Data Storage Platform"
echo "============================================"
echo

if ! command -v python3 >/dev/null 2>&1; then
    echo "[ERROR] python3 was not found on this computer."
    echo "Please install Python 3.9 or newer from https://www.python.org/downloads/"
    exit 1
fi

if [ ! -d "venv" ]; then
    echo "Creating a virtual environment in ./venv ..."
    python3 -m venv venv
fi

echo "Installing/updating dependencies from requirements.txt ..."
source venv/bin/activate
python -m pip install --upgrade pip >/dev/null
pip install -r requirements.txt

echo
echo "Starting BioVault. A browser tab should open automatically."
echo "Press CTRL+C in this terminal to stop the app."
echo
streamlit run app.py
