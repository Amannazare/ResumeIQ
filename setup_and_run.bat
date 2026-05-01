@echo off
echo Setting up Resume Analyser...
python -m venv .venv
call .venv\Scripts\activate
pip install -r requirements.txt
echo.
echo Setup complete! Starting app...
python app.py
