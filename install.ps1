# Installs "Can I Run AI?" for the current user on Windows (no admin needed).
#   irm https://raw.githubusercontent.com/YOUR_USER/YOUR_REPO/main/install.ps1 | iex
$ErrorActionPreference = "Stop"

$Repo = if ($env:CIRA_REPO) { $env:CIRA_REPO } else { "YOUR_USER/YOUR_REPO" }
$Url  = if ($env:CIRA_URL)  { $env:CIRA_URL }  else { "https://github.com/$Repo/releases/latest/download/can-i-run-ai.exe" }

if (-not $env:CIRA_URL -and $Repo -eq "YOUR_USER/YOUR_REPO") {
    Write-Host "Edit install.ps1 and set `$Repo to your GitHub repo (user/name) first." -ForegroundColor Red
    return
}

$Dir = Join-Path $env:LOCALAPPDATA "CanIRunAI"
New-Item -ItemType Directory -Force -Path $Dir | Out-Null
$Exe = Join-Path $Dir "can-i-run-ai.exe"

Write-Host "Downloading Can I Run AI?..."
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
Invoke-WebRequest -Uri $Url -OutFile $Exe -UseBasicParsing
Unblock-File $Exe

# Start Menu shortcut
$Shortcut = Join-Path ([Environment]::GetFolderPath("Programs")) "Can I Run AI.lnk"
$Shell = New-Object -ComObject WScript.Shell
$Link = $Shell.CreateShortcut($Shortcut)
$Link.TargetPath = $Exe
$Link.WorkingDirectory = $Dir
$Link.Save()

Write-Host "Installed to $Exe"
Write-Host "Find it in the Start Menu as 'Can I Run AI'."
Write-Host "To uninstall: delete $Dir and the Start Menu shortcut."
