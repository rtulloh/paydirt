#!/bin/bash
# Setup script for Paydirt Web Backend

echo "Setting up Paydirt Web Backend..."

# Check Python version
PYTHON_VERSION=$(python3 -c 'import sys; print(sys.version_info[1])')

if [ "$PYTHON_VERSION" -ge 12 ]; then
    echo "Python 3.$PYTHON_VERSION detected. Installing dependencies..."
    pip3 install -r requirements.txt
else
    echo "WARNING: Python 3.$PYTHON_VERSION detected."
    echo "FastAPI requires Python 3.12+ for prebuilt wheels."
    echo ""
    echo "Options:"
    echo "1. Install Python 3.12 via Homebrew: brew install python@3.12"
    echo "2. Use pyenv to manage Python versions"
    echo ""
    echo "After installing Python 3.12+, run this script again."
fi
