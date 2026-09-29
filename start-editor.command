#!/bin/bash
# Double-click this file (Mac) to open the QSTEAP website editor.
cd "$(dirname "$0")"
if ! command -v python3 >/dev/null; then echo "Python 3 is needed: https://www.python.org/downloads/"; read -p "Press Enter to close"; exit 1; fi
if [ ! -x .venv/bin/python ]; then
  echo "First run: setting up the editor (one time only)..."
  python3 -m venv .venv && .venv/bin/pip install -q -r editor/requirements.txt || { echo "Setup failed."; read -p "Press Enter to close"; exit 1; }
fi
if ! command -v quarto >/dev/null; then echo "NOTE: Quarto is not installed, so previews won't build. Get it at https://quarto.org/docs/get-started/"; fi
.venv/bin/python editor/app.py
