[CmdletBinding()]
param(
    [switch]$CheckOnly,
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$ThonnyArguments
)

$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$venvPython = Join-Path $projectRoot '.venv\Scripts\python.exe'
$userDir = Join-Path $projectRoot '.thonny-user'
if (-not (Test-Path -LiteralPath $venvPython)) {
    throw 'Run .\scripts\setup_windows.ps1 first.'
}

$previousUserDir = $env:THONNY_USER_DIR
$previousPath = $env:PATH
$env:THONNY_USER_DIR = $userDir
$env:PATH = (Split-Path -Parent $venvPython) + [System.IO.Path]::PathSeparator + $previousPath
Push-Location $projectRoot
try {
    & $venvPython -c "from pathlib import Path; import shutil; import minny, thonny; root = Path.cwd().resolve(); assert minny.__file__ and Path(minny.__file__).resolve().is_relative_to(root / 'minny'), 'Minny must be installed editable from this workspace'; assert thonny.__file__ and Path(thonny.__file__).resolve().is_relative_to(root / 'thonny'), 'Thonny must be installed editable from this workspace'; server = shutil.which('basedpyright-langserver'); assert server and Path(server).resolve().is_relative_to(root / '.venv'), 'The local basedpyright language server is missing'; print('Minny:', minny.__file__); print('Thonny:', thonny.__file__); print('Language server:', server); print('User data:', thonny.get_thonny_user_dir())"
    if ($LASTEXITCODE -ne 0) { throw 'Local editable installs or GUI dependencies are missing. Run setup_windows.ps1.' }
    if ($CheckOnly) { return }

    New-Item -ItemType Directory -Path $userDir -Force | Out-Null
    $configurationPath = Join-Path $userDir 'configuration.ini'
    if (-not (Test-Path -LiteralPath $configurationPath)) {
        # Seed only the isolated development profile. Later user choices persist.
        $initialConfiguration = @'
[general]
single_instance = False

[run]
backend_name = ESP32

[ESP32]
port = rfc2217://127.0.0.1:4000
'@
        [System.IO.File]::WriteAllText($configurationPath, $initialConfiguration, [System.Text.UTF8Encoding]::new($false))
    }

    # Keep a new development profile in the examples folder instead of the
    # Windows home directory, which can contain a very large Python workspace.
    $initialWorkingDirectory = Join-Path $projectRoot 'examples'
    $initializeWorkingDirectory = @'
import configparser
import pathlib
import sys
configuration = pathlib.Path(sys.argv[1])
settings = configparser.ConfigParser(interpolation=None)
settings.read(configuration, encoding='utf-8')
if not settings.has_section('run'):
    settings.add_section('run')
if not settings.get('run', 'working_directory', fallback='').strip():
    settings.set('run', 'working_directory', sys.argv[2])
    with configuration.open('w', encoding='utf-8') as target:
        settings.write(target)
'@
    & $venvPython -c $initializeWorkingDirectory $configurationPath $initialWorkingDirectory
    if ($LASTEXITCODE -ne 0) { throw 'Could not initialize the isolated working directory.' }

    # A distinct profile also keeps IPC separate from ordinary Thonny sessions.
    & $venvPython -m thonny --profile rfc2217-development @ThonnyArguments
    if ($LASTEXITCODE -ne 0) { throw "Thonny exited with code $LASTEXITCODE. See .thonny-user logs." }
}
finally {
    Pop-Location
    $env:THONNY_USER_DIR = $previousUserDir
    $env:PATH = $previousPath
}
