@echo off
REM Builds a single-file Windows app into dist\can-i-run-ai.exe
python -m pip install --upgrade pyinstaller -r requirements.txt || exit /b 1
python -m PyInstaller --onefile --windowed --name can-i-run-ai --icon icon.ico --add-data "models.json;." --add-data "icon.png;." --add-data "icon.ico;." --collect-all customtkinter can_i_run_ai.py || exit /b 1
echo Done: dist\can-i-run-ai.exe
