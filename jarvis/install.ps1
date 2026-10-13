# JARVIS installer for Windows 10/11.
# Run from PowerShell in this folder:
#   powershell -ExecutionPolicy Bypass -File .\install.ps1
#   powershell -ExecutionPolicy Bypass -File .\install.ps1 -Minimal   (no voice packages)
param([switch]$Minimal)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot
function Say($m)  { Write-Host "> $m" -ForegroundColor Cyan }
function Ok($m)   { Write-Host "+ $m" -ForegroundColor Green }
function Warn($m) { Write-Host "! $m" -ForegroundColor Yellow }
function Die($m)  { Write-Host "x $m" -ForegroundColor Red; exit 1 }

function Refresh-Path {
    $env:Path = [Environment]::GetEnvironmentVariable("Path", "Machine") + ";" +
                [Environment]::GetEnvironmentVariable("Path", "User")
}

function Find-Python {
    foreach ($cmd in @(@("py", "-3.13"), @("py", "-3.12"), @("py", "-3.11"), @("python"), @("python3"))) {
        try {
            $exe = $cmd[0]; $rest = @($cmd | Select-Object -Skip 1)
            & $exe @rest -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)" 2>$null
            if ($LASTEXITCODE -eq 0) {
                return (& $exe @rest -c "import sys; print(sys.executable)").Trim()
            }
        } catch { }
    }
    return $null
}

# ------------------------------------------------------------------ Python
Say "Checking Python"
$py = Find-Python
if (-not $py) {
    if (Get-Command winget -ErrorAction SilentlyContinue) {
        Say "Installing Python 3.12 with winget"
        winget install --id Python.Python.3.12 -e --accept-source-agreements --accept-package-agreements
        Refresh-Path
        $py = Find-Python
    }
    if (-not $py) { Die "Python 3.11+ is required. Install it from https://www.python.org/downloads/ (tick 'Add to PATH') and re-run." }
}
Ok "Using Python at $py"

# ------------------------------------------------------------------ venv
Say "Creating virtual environment (.venv)"
& $py -m venv .venv
$vpy = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
& $vpy -m pip install --quiet --upgrade pip
if ($Minimal) {
    & $vpy -m pip install --quiet -e ".[system,docs]"
} else {
    & $vpy -m pip install --quiet -e ".[all]"
    if ($LASTEXITCODE -ne 0) {
        Warn "Some optional packages failed; installing the core with system extras only."
        & $vpy -m pip install --quiet -e ".[system,docs]"
    }
}
Ok "Python packages installed"

# ------------------------------------------------------------------ Ollama
Say "Checking Ollama (local model runtime)"
if (-not (Get-Command ollama -ErrorAction SilentlyContinue)) {
    if (Get-Command winget -ErrorAction SilentlyContinue) {
        winget install --id Ollama.Ollama -e --accept-source-agreements --accept-package-agreements
        Refresh-Path
        $local = Join-Path $env:LOCALAPPDATA "Programs\Ollama"
        if (Test-Path $local) { $env:Path += ";$local" }
    }
    if (-not (Get-Command ollama -ErrorAction SilentlyContinue)) {
        Start-Process "https://ollama.com/download"
        Die "Install Ollama from https://ollama.com/download, then re-run this script."
    }
}
Ok "Ollama installed"

function Test-Ollama {
    try { Invoke-RestMethod -Uri "http://localhost:11434/api/tags" -TimeoutSec 2 | Out-Null; return $true }
    catch { return $false }
}
if (-not (Test-Ollama)) {
    Say "Starting the Ollama server"
    Start-Process ollama -ArgumentList "serve" -WindowStyle Hidden
    for ($i = 0; $i -lt 30 -and -not (Test-Ollama); $i++) { Start-Sleep -Seconds 1 }
}
if (-not (Test-Ollama)) { Die "Ollama did not start. Open the Ollama app from the Start menu and re-run." }
Ok "Ollama is running"

# ------------------------------------------------------------------ models + config
Say "Creating config and downloading models (several GB on first run)"
& $vpy -m jarvis setup

# ------------------------------------------------------------------ shortcut
try {
    $shell = New-Object -ComObject WScript.Shell
    $lnk = $shell.CreateShortcut((Join-Path ([Environment]::GetFolderPath("Desktop")) "JARVIS.lnk"))
    $lnk.TargetPath = Join-Path $PSScriptRoot "jarvis.bat"
    $lnk.Arguments = "web"
    $lnk.WorkingDirectory = $PSScriptRoot
    $lnk.Description = "JARVIS local AI"
    $lnk.Save()
    Ok "Desktop shortcut 'JARVIS' created (opens the HUD)"
} catch { Warn "Could not create a desktop shortcut: $_" }

Ok "Installed!"
Write-Host ""
Write-Host "  .\jarvis.bat          chat in the terminal"
Write-Host "  .\jarvis.bat web      holographic HUD in your browser"
Write-Host "  .\jarvis.bat voice    hands-free: say 'Jarvis, ...'"
Write-Host "  .\jarvis.bat doctor   check everything"
