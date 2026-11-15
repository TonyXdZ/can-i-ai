#!/usr/bin/env bash
# Builds a single-file Linux binary into dist/can-i-run-ai
set -e
python3 -m pip install --upgrade pyinstaller -r requirements.txt
python3 -m PyInstaller --onefile --windowed --name can-i-run-ai \
  --add-data "models.json:." --collect-all customtkinter can_i_run_ai.py
echo "Done: dist/can-i-run-ai"
