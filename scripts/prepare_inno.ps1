[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$toolsRoot = Join-Path $projectRoot 'build-tools'
$downloadDirectory = Join-Path $toolsRoot 'downloads'
$compilerDirectory = Join-Path $toolsRoot 'inno'
$compilerPath = Join-Path $compilerDirectory 'ISCC.exe'
$installerPath = Join-Path $downloadDirectory 'innosetup-6.7.4.exe'
$installerUrl = 'https://github.com/jrsoftware/issrc/releases/download/is-6_7_4/innosetup-6.7.4.exe'
$expectedHash = 'A549929319F9120716677C685535CA4671E4B937B5FDC87E2585F32D8EB30E8C'

if (Test-Path -LiteralPath $compilerPath) {
    Write-Output $compilerPath
    return
}

New-Item -ItemType Directory -Path $downloadDirectory -Force | Out-Null
if (-not (Test-Path -LiteralPath $installerPath)) {
    Invoke-WebRequest -Uri $installerUrl -OutFile $installerPath -UseBasicParsing
}

$actualHash = (Get-FileHash -LiteralPath $installerPath -Algorithm SHA256).Hash
if ($actualHash -ne $expectedHash) {
    throw "Inno Setup installer checksum mismatch: $actualHash"
}
$signature = Get-AuthenticodeSignature -LiteralPath $installerPath
if ($signature.Status -ne 'Valid' -or $signature.SignerCertificate.Subject -notmatch 'CN=Pyrsys B\.V\.') {
    throw 'The downloaded Inno Setup installer does not have the expected valid publisher signature.'
}

# Inno Setup's own /PORTABLE=1 mode skips registry/association/uninstaller
# registration. The compiler remains contained in this workspace.
$installerArguments = @(
    '/PORTABLE=1', '/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART',
    '/CURRENTUSER', '/NOICONS', '/TASKS=""',
    ('/DIR="' + $compilerDirectory + '"'),
    ('/LOG="' + (Join-Path $toolsRoot 'inno-install.log') + '"')
)
$installerProcess = Start-Process -FilePath $installerPath -ArgumentList $installerArguments -WindowStyle Hidden -Wait -PassThru
if ($installerProcess.ExitCode -ne 0 -or -not (Test-Path -LiteralPath $compilerPath)) {
    throw "Could not prepare the local Inno Setup compiler (exit $($installerProcess.ExitCode))."
}
Write-Output $compilerPath
