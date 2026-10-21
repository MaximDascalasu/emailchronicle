param(
    [string]$Python = ".venv\Scripts\python.exe",
    [string]$Iscc = "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
    [string]$OutputDirectory = 'installer-output',
    [switch]$RequireSigning,
    [switch]$PackageUnverifiedPreview,
    [string]$CertificateThumbprint = $env:EMAILCHRONICLE_SIGNING_THUMBPRINT,
    [string]$Publisher = $env:EMAILCHRONICLE_PUBLISHER,
    [string]$TimestampUrl = 'http://timestamp.digicert.com',
    [string]$SignTool = ''
)
$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)
$OutputDirectory = [IO.Path]::GetFullPath($OutputDirectory)
New-Item -ItemType Directory -Path $OutputDirectory -Force | Out-Null
if (-not $Publisher) { $Publisher = 'EmailChronicle' }
if ($PackageUnverifiedPreview -and $RequireSigning) { throw 'Unverified packaging is allowed only for unsigned local previews' }
if ($RequireSigning -and -not $CertificateThumbprint) { throw 'Signed release blocked: no code-signing certificate configured' }
if ($RequireSigning) {
    $distribution = Get-Content 'packaging\distribution-status.json' -Raw | ConvertFrom-Json
    if ($distribution.application_license -eq 'pending-owner-decision' -or
        $distribution.runtime_redistribution_review -ne 'complete' -or
        -not $distribution.reviewed_by -or $distribution.publisher -ne $Publisher) {
        throw 'Signed release blocked: publisher/license/redistribution review incomplete; see docs/DISTRIBUTION.md'
    }
}
if (-not (Test-Path -LiteralPath $Iscc)) { throw 'Install the Inno Setup compiler or pass -Iscc; no installer can be produced without it' }
if ($CertificateThumbprint) {
    & "$PSScriptRoot\sign-windows.ps1" -FilePath "$PSScriptRoot\build-windows.ps1" -CertificateThumbprint $CertificateThumbprint -Publisher $Publisher -TimestampUrl $TimestampUrl -SignTool $SignTool -CheckOnly
}
function Assert-Exit([string]$Step) {
    if ($LASTEXITCODE -ne 0) { throw "$Step failed ($LASTEXITCODE)" }
}
& $Python -m pytest -q
Assert-Exit "Tests"
& $Python packaging\compliance.py
Assert-Exit "License/source collection"
& $Python -m PyInstaller --noconfirm --clean packaging\EmailChronicle.spec
Assert-Exit "Executable build"
if ($CertificateThumbprint) {
    foreach ($binary in Get-ChildItem 'dist\EmailChronicle' -Recurse -File | Where-Object Extension -In '.exe','.dll','.pyd') {
        $signature = Get-AuthenticodeSignature -LiteralPath $binary.FullName
        if ($signature.Status -eq 'Valid') { continue } # Retain trusted upstream signatures.
        if ($signature.Status -ne 'NotSigned') { throw "Invalid upstream binary signature: $($binary.Name)" }
        & "$PSScriptRoot\sign-windows.ps1" -FilePath $binary.FullName -CertificateThumbprint $CertificateThumbprint -Publisher $Publisher -TimestampUrl $TimestampUrl -SignTool $SignTool
    }
}
& $Python packaging\compliance.py --inventory dist\EmailChronicle
Assert-Exit "Bundle/license inventory"
$report = Join-Path (Get-Location) "build\smoke-report.json"
if (Test-Path -LiteralPath $report) { Remove-Item -LiteralPath $report }
$smokeVerified = $false
$previousQtPlatform = $env:QT_QPA_PLATFORM
$env:QT_QPA_PLATFORM = "offscreen"
try {
    $process = Start-Process -FilePath "dist\EmailChronicle\EmailChronicle.exe" -ArgumentList @("--smoke-test", "`"$report`"") -WindowStyle Hidden -PassThru
    if (-not $process.WaitForExit(60000)) { $process.Kill(); throw "Executable smoke test timed out" }
    if ($process.ExitCode -ne 0 -or -not (Test-Path -LiteralPath $report)) { throw "Executable smoke test failed" }
    $smokeResult = Get-Content -LiteralPath $report -Raw | ConvertFrom-Json
    if ($smokeResult.status -ne 'ok' -or -not $smokeResult.eml -or -not $smokeResult.msg -or -not $smokeResult.mixed_email_import) { throw 'EML/MSG smoke verification failed' }
    $smokeVerified = $true
} catch {
    if (-not $PackageUnverifiedPreview) { throw }
    @{status='unverified'; error=$_.Exception.Message; security_controls_unchanged=$true} |
        ConvertTo-Json | Set-Content -Encoding utf8 $report
    Write-Warning 'Packaging an UNSIGNED, UNVERIFIED local preview. No security controls have been bypassed.'
} finally {
    if ($null -eq $previousQtPlatform) {
        Remove-Item Env:\QT_QPA_PLATFORM -ErrorAction SilentlyContinue
    } else {
        $env:QT_QPA_PLATFORM = $previousQtPlatform
    }
}
$version = & $Python -c "import importlib.metadata; print(importlib.metadata.version('emailchronicle'))"
Assert-Exit "Version lookup"
& $Python packaging\compliance.py --source-companion $OutputDirectory
Assert-Exit "Source companion archive"
$sourceCompanion = Join-Path $OutputDirectory "EmailChronicle-ThirdPartySources-$version.zip"
$compilerArgs = @("/DAppVersion=$version", "/DAppPublisher=$Publisher", "/O$OutputDirectory", "/DSourceCompanion=$sourceCompanion")
if ($CertificateThumbprint) {
    # Inno substitutes $q with quotes and $f with the quoted setup/uninstall file.
    # Signing settings are public identity/configuration only, never key material.
    $signScript = (Resolve-Path "$PSScriptRoot\sign-windows.ps1").Path
    $signCommand = 'powershell.exe -NoProfile -File $q' + $signScript + '$q -FilePath $f -CertificateThumbprint ' + $CertificateThumbprint + ' -Publisher $q' + $Publisher + '$q -TimestampUrl $q' + $TimestampUrl + '$q'
    if ($SignTool) { $signCommand += ' -SignTool $q' + $SignTool + '$q' }
    $compilerArgs += @('/DSignRelease', ('/Schronicle=' + $signCommand))
}
& $Iscc @compilerArgs packaging\installer.iss
Assert-Exit "Installer build"
$artifact = Get-Item (Join-Path $OutputDirectory "EmailChronicle-Setup-$version-x64.exe")
if ($CertificateThumbprint -and (Get-AuthenticodeSignature -LiteralPath $artifact.FullName).Status -ne 'Valid') {
    throw 'Setup signature is not valid'
}
Copy-Item 'dist\EmailChronicle\bundle-inventory.json' (Join-Path $OutputDirectory 'bundle-inventory.json')
Copy-Item 'THIRD_PARTY_NOTICES.md' (Join-Path $OutputDirectory 'THIRD_PARTY_NOTICES.md')
$signed = [bool]$CertificateThumbprint
@{signed=$signed; publisher=$Publisher; version=$version; certificate_thumbprint=$CertificateThumbprint;
  packaged_smoke_verified=$smokeVerified; clean_machine_verified=$false; distribution_status='preview-final-acceptance-pending'} |
    ConvertTo-Json | Set-Content -Encoding utf8 (Join-Path $OutputDirectory 'signing-status.json')
Copy-Item -LiteralPath $report -Destination (Join-Path $OutputDirectory 'packaged-smoke-report.json')
Get-ChildItem $OutputDirectory -File | Where-Object Name -NE 'SHA256SUMS.txt' | ForEach-Object {
    $hash = (Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
    "$hash  $($_.Name)"
} | Set-Content -Encoding ascii (Join-Path $OutputDirectory 'SHA256SUMS.txt')
Write-Host "Installer ready: $($artifact.FullName)"
