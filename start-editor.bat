@echo off
REM Double-click this file (Windows) to open the QSTEAP website editor.
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (
  echo First run: setting up the editor ^(one time only^)...
  python -m venv .venv || (echo Python 3 is needed: https://www.python.org/downloads/ & pause & exit /b 1)
  .venv\Scripts\pip install -q -r editor\requirements.txt
)
.venv\Scripts\python editor\app.py
pause
