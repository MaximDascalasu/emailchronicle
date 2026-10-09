param(
    [string]$Python = ".venv\Scripts\python.exe",
    [string]$Iscc = "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe"
)
$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)
function Assert-Exit([string]$Step) {
    if ($LASTEXITCODE -ne 0) { throw "$Step failed ($LASTEXITCODE)" }
}
& $Python -m pytest -q
Assert-Exit "Tests"
& $Python -m PyInstaller --noconfirm --clean packaging\EmailChronicle.spec
Assert-Exit "Executable build"
$report = Join-Path (Get-Location) "build\smoke-report.json"
if (Test-Path -LiteralPath $report) { Remove-Item -LiteralPath $report }
$previousQtPlatform = $env:QT_QPA_PLATFORM
$env:QT_QPA_PLATFORM = "offscreen"
try {
    $process = Start-Process -FilePath "dist\EmailChronicle\EmailChronicle.exe" -ArgumentList @("--smoke-test", "`"$report`"") -WindowStyle Hidden -PassThru
    if (-not $process.WaitForExit(60000)) { $process.Kill(); throw "Executable smoke test timed out" }
    if ($process.ExitCode -ne 0 -or -not (Test-Path -LiteralPath $report)) { throw "Executable smoke test failed" }
    if ((Get-Content -LiteralPath $report -Raw | ConvertFrom-Json).status -ne "ok") { throw "Invalid smoke report" }
} finally {
    if ($null -eq $previousQtPlatform) {
        Remove-Item Env:\QT_QPA_PLATFORM -ErrorAction SilentlyContinue
    } else {
        $env:QT_QPA_PLATFORM = $previousQtPlatform
    }
}
$version = & $Python -c "import importlib.metadata; print(importlib.metadata.version('emailchronicle'))"
Assert-Exit "Version lookup"
& $Iscc "/DAppVersion=$version" packaging\installer.iss
Assert-Exit "Installer build"
$artifact = Get-Item "installer-output\EmailChronicle-Setup-$version-x64.exe"
$hash = (Get-FileHash -LiteralPath $artifact.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
"$hash  $($artifact.Name)" | Set-Content -Encoding ascii "installer-output\SHA256SUMS.txt"
Write-Host "Installer ready: $($artifact.FullName)"
