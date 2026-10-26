@echo off
setlocal
cd /d "%~dp0"

python -m pip install -r requirements.txt
python -m pip install -r requirements-build.txt
python -m PyInstaller --clean --noconfirm --workpath "%TEMP%\RoutineIA_pyinstaller_build" RoutineIA.spec

echo.
echo Build desktop concluido: dist\RoutineIA.exe
echo Para criar atalho: powershell -ExecutionPolicy Bypass -File create_desktop_shortcut.ps1
endlocal
