[CmdletBinding()]
param(
    [string]$Version = '0.1.0',
    [string]$SourceRoot = (Split-Path -Parent $PSScriptRoot),
    [string]$OutputDirectory = '',
    [switch]$Reuse,
    [switch]$BundleOnly
)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
if (-not $OutputDirectory) { $OutputDirectory = Join-Path $projectRoot 'build\bundle' }
$OutputDirectory = [System.IO.Path]::GetFullPath($OutputDirectory)
$python = Join-Path $projectRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $python)) { throw 'Prepare .venv with setup_windows.ps1 first.' }
$buildArguments = @((Join-Path $projectRoot 'packaging\windows\build_bundle.py'), '--source-root', $SourceRoot, '--output-dir', $OutputDirectory, '--version', $Version)
if ($Reuse) { $buildArguments += '--reuse' }
& $python @buildArguments
if ($LASTEXITCODE -ne 0) { throw 'The application bundle build failed.' }
Write-Host "Bundle ready at $OutputDirectory"
if ($BundleOnly) { return }
$compiler = & (Join-Path $PSScriptRoot 'prepare_inno.ps1')
$distDirectory = Join-Path $projectRoot 'dist'
New-Item -ItemType Directory -Path $distDirectory -Force | Out-Null
& $compiler ("/DSourceFolder=$OutputDirectory") ("/DOutputDir=$distDirectory") ("/DAppVersion=$Version") (Join-Path $projectRoot 'packaging\windows\installer.iss')
if ($LASTEXITCODE -ne 0) { throw 'Installer compilation failed.' }
$portableArchive = Join-Path $distDirectory "Thonny-RFC2217-$Version-windows-x64-portable.zip"
& $python (Join-Path $projectRoot 'packaging\windows\create_portable.py') --bundle $OutputDirectory --output $portableArchive --version $Version
if ($LASTEXITCODE -ne 0) { throw 'Portable archive creation failed.' }
$checksumPath = Join-Path $distDirectory 'SHA256SUMS.txt'
$releaseFiles = Get-ChildItem -LiteralPath $distDirectory -File | Where-Object { $_.Name -like "Thonny-RFC2217-$Version-windows-x64-*" }
$checksumLines = $releaseFiles | Sort-Object Name | ForEach-Object { $digest = (Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash.ToLowerInvariant(); "$digest  $($_.Name)" }
[System.IO.File]::WriteAllLines($checksumPath, $checksumLines, [System.Text.UTF8Encoding]::new($false))
Write-Host "Installer, portable ZIP, and checksums ready at $distDirectory"
