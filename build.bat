@echo off
REM Builds a single-file Windows app into dist\can-i-run-ai.exe
python -m pip install --upgrade pyinstaller -r requirements.txt || exit /b 1
python -m PyInstaller --onefile --windowed --name can-i-run-ai --add-data "models.json;." --collect-all customtkinter can_i_run_ai.py || exit /b 1
echo Done: dist\can-i-run-ai.exe
