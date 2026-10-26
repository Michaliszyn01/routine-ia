$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$ExePath = Join-Path $ProjectRoot "dist\RoutineIA.exe"
$IconPath = Join-Path $ProjectRoot "frontend\static\assets\icon.ico"
$DesktopPath = [Environment]::GetFolderPath("Desktop")
$ShortcutPath = Join-Path $DesktopPath "Routine IA.lnk"

if (-not (Test-Path -LiteralPath $ExePath)) {
    throw "Executavel nao encontrado em: $ExePath. Gere o build antes de criar o atalho."
}

if (-not (Test-Path -LiteralPath $IconPath)) {
    throw "Icone nao encontrado em: $IconPath"
}

$Shell = New-Object -ComObject WScript.Shell
$Shortcut = $Shell.CreateShortcut($ShortcutPath)
$Shortcut.TargetPath = $ExePath
$Shortcut.WorkingDirectory = Split-Path -Parent $ExePath
$Shortcut.IconLocation = $IconPath
$Shortcut.Description = "Routine IA / Life OS"
$Shortcut.Save()

Write-Host "Atalho criado: $ShortcutPath"
