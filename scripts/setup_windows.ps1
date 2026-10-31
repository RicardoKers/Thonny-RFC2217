[CmdletBinding()]
param(
    [string]$PythonCommand = 'python'
)

$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$venvPython = Join-Path $projectRoot '.venv\Scripts\python.exe'

Push-Location $projectRoot
try {
    foreach ($sourcePath in @('minny\pyproject.toml', 'thonny\pyproject.toml')) {
        if (-not (Test-Path -LiteralPath $sourcePath)) {
            throw "Source checkout missing: $sourcePath. Keep the minny and thonny folders beside scripts."
        }
    }

    if (-not (Test-Path -LiteralPath $venvPython)) {
        & $PythonCommand -c "import sys; assert sys.version_info >= (3, 11), 'Python 3.11 or newer is required'; import tkinter; print(sys.executable)"
        if ($LASTEXITCODE -ne 0) { throw 'Python 3.11+ with Tkinter is required.' }
        & $PythonCommand -m venv (Join-Path $projectRoot '.venv')
        if ($LASTEXITCODE -ne 0) { throw 'Could not create the isolated virtual environment.' }
    }

    & $venvPython -c "import sys, tkinter; assert sys.version_info >= (3, 11), 'Python 3.11 or newer is required'"
    if ($LASTEXITCODE -ne 0) { throw 'The existing .venv must use Python 3.11+ with Tkinter.' }

    & $venvPython -m pip install --upgrade pip
    if ($LASTEXITCODE -ne 0) { throw 'Could not update pip inside .venv.' }

    & $venvPython -m pip install -e (Join-Path $projectRoot 'minny') -e (Join-Path $projectRoot 'thonny') -r (Join-Path $projectRoot 'requirements-dev.txt')
    if ($LASTEXITCODE -ne 0) { throw 'Could not install the local projects and development dependencies.' }

    & $venvPython -c "from pathlib import Path; import minny, thonny, serial, tkinter; root = Path.cwd().resolve(); assert minny.__file__ and Path(minny.__file__).resolve().is_relative_to(root / 'minny'), 'Minny must be installed editable from this workspace'; assert thonny.__file__ and Path(thonny.__file__).resolve().is_relative_to(root / 'thonny'), 'Thonny must be installed editable from this workspace'; print('Minny:', minny.__file__); print('Thonny:', thonny.__file__); print('PySerial:', serial.VERSION)"
    if ($LASTEXITCODE -ne 0) { throw 'The environment is not using the local source checkouts.' }

    Write-Host 'Environment ready. Start with: .\scripts\run_thonny.ps1'
}
finally {
    Pop-Location
}
