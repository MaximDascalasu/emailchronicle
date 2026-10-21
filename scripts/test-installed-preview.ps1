param(
    [Parameter(Mandatory=$true)][string]$Installer,
    [string]$OutputDirectory = 'build/preview-verification',
    [ValidateSet('developer-host-not-clean','clean-windows-vm')][string]$EnvironmentLabel = 'developer-host-not-clean',
    [int]$Launches = 10
)
$ErrorActionPreference = 'Stop'
$installerPath = (Resolve-Path -LiteralPath $Installer).Path
$outputRoot = [IO.Path]::GetFullPath($OutputDirectory)
New-Item -ItemType Directory -Path $outputRoot -Force | Out-Null
$runRoot = Join-Path $outputRoot ('installation-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $runRoot | Out-Null
$installDirectory = Join-Path $runRoot 'program'
$reportPath = Join-Path $runRoot 'installation-test.json'
$report = [ordered]@{
    environment=$EnvironmentLabel; clean_machine_independently_verified=$false
    windows=[Environment]::OSVersion.VersionString
    installer=$installerPath; installer_sha256=(Get-FileHash -LiteralPath $installerPath -Algorithm SHA256).Hash.ToLowerInvariant()
    authenticode=[string](Get-AuthenticodeSignature -LiteralPath $installerPath).Status
    security_controls_unchanged=$true; installation='not_run'; launches=@(); uninstallation='not_run'
}
function Run-Checked([string]$File, [array]$Arguments, [int]$Timeout=90) {
    $child = Start-Process -FilePath $File -ArgumentList $Arguments -WindowStyle Hidden -PassThru
    if (-not $child.WaitForExit($Timeout*1000)) { $child.Kill(); throw "Timed out: $File" }
    if ($child.ExitCode -ne 0) { throw "Process failed ($($child.ExitCode)): $File" }
}
$installed = $false
$sentinel = $null
$normal = $null
$inheritedEnvironment = @{}
try {
    $registration = 'Software/Microsoft/Windows/CurrentVersion/Uninstall/{AA579A1A-4BBD-41A2-B704-5B8F5DEBE19B}_is1'
    if ((Test-Path "HKCU:/$registration") -or (Test-Path "HKLM:/$registration")) {
        throw 'Existing EmailChronicle installation found. Use a separate Windows test account or VM; no existing installation was modified.'
    }
    Run-Checked $installerPath @('/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART',('/DIR="'+$installDirectory+'"'),('/LOG="'+(Join-Path $runRoot 'setup.log')+'"'))
    $installed = $true
    $report.installation='passed'
    $exe = Join-Path $installDirectory 'EmailChronicle.exe'
    $inventory = Get-Content -LiteralPath (Join-Path $installDirectory 'bundle-inventory.json') -Raw | ConvertFrom-Json
    foreach ($file in $inventory.files) {
        $installedPath = Join-Path $installDirectory $file.path
        if (-not (Test-Path -LiteralPath $installedPath) -or (Get-FileHash -LiteralPath $installedPath -Algorithm SHA256).Hash.ToLowerInvariant() -ne $file.sha256) {
            throw "Installed runtime missing or changed: $($file.path)"
        }
    }
    $report.runtime_inventory='passed'
    $embeddedSources = Join-Path $installDirectory '_internal/third-party-notices/ThirdPartySources.zip'
    if (-not (Test-Path -LiteralPath $embeddedSources)) { throw 'The single installer omitted its required source companion' }
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $archive = [IO.Compression.ZipFile]::OpenRead($embeddedSources)
    try {
        $indexEntry = $archive.GetEntry('notices/source-index.json')
        if (-not $indexEntry) { throw 'Embedded source provenance missing' }
        $reader = [IO.StreamReader]::new($indexEntry.Open())
        try { $index = $reader.ReadToEnd() | ConvertFrom-Json } finally { $reader.Dispose() }
        foreach ($source in $index) {
            $entry = $archive.GetEntry('sources/' + ($source.url.Split('/')[-1]))
            if (-not $entry) { throw 'Embedded upstream source archive missing' }
            $stream = $entry.Open()
            $hash = [Security.Cryptography.SHA256]::Create()
            try { $digest = [BitConverter]::ToString($hash.ComputeHash($stream)).Replace('-','').ToLowerInvariant() }
            finally { $stream.Dispose(); $hash.Dispose() }
            if ($digest -ne $source.sha256) { throw 'Embedded upstream source checksum mismatch' }
        }
    } finally { $archive.Dispose() }
    if (-not (Test-Path -LiteralPath (Join-Path $installDirectory 'QUICK-START.txt'))) { throw 'Quick start missing' }
    $report.single_installer_sources_and_guide='passed'
    # Prove the installed runtime does not need developer Python/Qt on PATH.
    foreach ($name in @('PATH','PYTHONPATH','PYTHONHOME','QT_PLUGIN_PATH','QT_QPA_PLATFORM_PLUGIN_PATH')) {
        $inheritedEnvironment[$name] = [Environment]::GetEnvironmentVariable($name, 'Process')
        [Environment]::SetEnvironmentVariable($name, $null, 'Process')
    }
    $env:PATH = "$env:SystemRoot\System32;$env:SystemRoot"
    $report.developer_runtime_paths_removed=$true
    # Start the normal application entry point with an isolated synthetic case
    # directory, then request a normal window close (never terminate to pass).
    $normalData = Join-Path $runRoot 'normal-launch-data'
    $normal = Start-Process -FilePath $exe -ArgumentList @('--data-dir', ('"'+$normalData+'"'), '--test-close-after-ms', '2000') -WindowStyle Hidden -PassThru
    $ready = $normal.WaitForInputIdle(20000)
    Start-Sleep -Milliseconds 500
    $normal.Refresh()
    if (-not $ready -or $normal.HasExited -or -not (Test-Path -LiteralPath (Join-Path $normalData 'chronicle.sqlite3'))) {
        throw 'Normal application launch did not initialise'
    }
    if (-not $normal.WaitForExit(20000)) { throw 'Normal application shutdown timed out (process retained for investigation)' }
    if ($normal.ExitCode -ne 0) { throw "Normal shutdown failed ($($normal.ExitCode))" }
    $report.normal_launch_and_shutdown='passed'
    $previousPlatform = $env:QT_QPA_PLATFORM
    try {
        $env:QT_QPA_PLATFORM='windows'
        for ($i=1; $i -le $Launches; $i++) {
            $smoke = Join-Path $runRoot "launch-$i.json"
            Run-Checked $exe @('--smoke-test',('"'+$smoke+'"'))
            $result = Get-Content -LiteralPath $smoke -Raw | ConvertFrom-Json
            if ($result.status -ne 'ok' -or -not $result.eml -or -not $result.msg -or -not $result.mixed_email_import) { throw 'Installed application smoke failed' }
            $report.launches += @{run=$i; exit_code=0; result=$result}
        }
    } finally {
        if ($null -eq $previousPlatform) { Remove-Item Env:/QT_QPA_PLATFORM -ErrorAction SilentlyContinue }
        else { $env:QT_QPA_PLATFORM=$previousPlatform }
    }
    $data = Join-Path $env:LOCALAPPDATA 'EmailChronicle'
    New-Item -ItemType Directory -Path $data -Force | Out-Null
    $sentinel = Join-Path $data ('synthetic-uninstall-check-' + [guid]::NewGuid().ToString('N') + '.txt')
    'Synthetic preservation check; no real evidence.' | Set-Content -LiteralPath $sentinel
    $report.status='passed-on-labelled-environment'
} catch {
    $report.status='blocked_or_failed'
    $report.error=$_.Exception.Message
} finally {
    foreach ($name in $inheritedEnvironment.Keys) {
        [Environment]::SetEnvironmentVariable($name, $inheritedEnvironment[$name], 'Process')
    }
    if ($normal -and -not $normal.HasExited) {
        # Only the test-owned process with an isolated synthetic data directory.
        # Forced cleanup is recorded as a failure, never a successful shutdown.
        $normal.Kill()
        $normal.WaitForExit()
        $report.normal_launch_and_shutdown='failed; test process terminated for cleanup'
        $report.status='blocked_or_failed'
    }
    if ($installed) {
        try {
            Run-Checked (Join-Path $installDirectory 'unins000.exe') @('/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART')
            for ($attempt=0; $attempt -lt 20 -and (Test-Path -LiteralPath (Join-Path $installDirectory 'EmailChronicle.exe')); $attempt++) { Start-Sleep -Milliseconds 250 }
            if (Test-Path -LiteralPath (Join-Path $installDirectory 'EmailChronicle.exe')) { throw 'Application remained after uninstall' }
            if ($sentinel -and -not (Test-Path -LiteralPath $sentinel)) { throw 'Uninstall removed synthetic workspace marker' }
            $report.uninstallation='passed'
            if ($sentinel) { Remove-Item -LiteralPath $sentinel }
        } catch { $report.uninstallation='blocked_or_failed'; $report.uninstall_error=$_.Exception.Message; $report.status='blocked_or_failed' }
    }
    $report | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $reportPath -Encoding utf8
    Write-Host "Installation test report: $reportPath"
}
if ($report.status -ne 'passed-on-labelled-environment') { throw $report.error }
