#!/usr/bin/env bash

set -e

VENV_DIR=".venv"

echo "Setting up Python virtual environment..."

if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment..."
    python3 -m venv $VENV_DIR
else
    echo "Virtual environment already exists."
fi

echo "Activating virtual environment..."
source $VENV_DIR/bin/activate

echo "Upgrading pip..."
pip install --upgrade pip

echo "Installing dependencies..."
pip install -r requirements.txt

echo ""
echo "Environment ready."
echo "Activate later with:"
echo "source .venv/bin/activate"