[CmdletBinding()]
param(
    [switch]$FullMinny,
    [switch]$Integration,
    [string]$Url = 'rfc2217://127.0.0.1:4000'
)

$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$venvPython = Join-Path $projectRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $venvPython)) {
    throw 'Run .\scripts\setup_windows.ps1 first.'
}

function Invoke-CheckedPython {
    param([string[]]$PythonArguments)
    & $venvPython @PythonArguments
    if ($LASTEXITCODE -ne 0) { throw "Test command failed with code $LASTEXITCODE." }
}

Push-Location (Join-Path $projectRoot 'minny')
try {
    # The wider upstream suite also tests package builders and Windows path handling.
    $minnyTestPath = if ($FullMinny) { 'tests' } else { 'tests/test_serial_connection.py' }
    Invoke-CheckedPython -PythonArguments @('-m', 'pytest', $minnyTestPath, '-m', 'not slow', '-q', '--tb=short')
}
finally { Pop-Location }

Push-Location (Join-Path $projectRoot 'thonny')
try {
    Invoke-CheckedPython -PythonArguments @('-m', 'pytest', 'thonny/test', '-q', '--tb=short')
}
finally { Pop-Location }

Push-Location $projectRoot
try {
    $workspaceTests = @(Get-ChildItem -LiteralPath (Join-Path $projectRoot 'tests') -Filter 'test_*.py' -File -ErrorAction SilentlyContinue)
    if ($workspaceTests.Count -gt 0) {
        Invoke-CheckedPython -PythonArguments @('-m', 'pytest', 'tests', '-q', '--tb=short')
    }
    if ($Integration) {
        $integrationScript = Join-Path $projectRoot 'tests\integration_simnodus.py'
        if (-not (Test-Path -LiteralPath $integrationScript)) {
            throw 'The integration runner tests\integration_simnodus.py is missing.'
        }
        Invoke-CheckedPython -PythonArguments @($integrationScript, '--url', $Url)
    }
}
finally { Pop-Location }
