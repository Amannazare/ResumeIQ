#!/bin/bash
echo "Setting up Resume Analyser..."
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
echo ""
echo "Setup complete! Starting app..."
python app.py
