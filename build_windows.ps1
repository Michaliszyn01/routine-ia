$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ProjectRoot

python -m pip install -r requirements.txt
python -m pip install -r requirements-build.txt
$WorkPath = Join-Path $env:TEMP "RoutineIA_pyinstaller_build"
python -m PyInstaller --clean --noconfirm --workpath $WorkPath RoutineIA.spec

Write-Host ""
Write-Host "Build desktop concluido: dist\RoutineIA.exe"
Write-Host "Para criar atalho: .\create_desktop_shortcut.ps1"
