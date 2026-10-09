param(
    [Parameter(Mandatory = $true)][string]$FilePath,
    [Parameter(Mandatory = $true)][ValidatePattern('^[A-Fa-f0-9]{40}$')][string]$CertificateThumbprint,
    [Parameter(Mandatory = $true)][string]$Publisher,
    [string]$TimestampUrl = 'http://timestamp.digicert.com',
    [string]$SignTool = '',
    [switch]$CheckOnly
)
$ErrorActionPreference = 'Stop'
if ($TimestampUrl -notmatch '^https?://') { throw 'A valid RFC3161 timestamp URL is required' }
$certificate = Get-Item -LiteralPath "Cert:\CurrentUser\My\$CertificateThumbprint" -ErrorAction Stop
if (-not $certificate.HasPrivateKey -or $certificate.NotAfter -le (Get-Date) -or $certificate.NotBefore -gt (Get-Date)) {
    throw 'Code-signing certificate must have an accessible private key and be within its validity period'
}
if ($certificate.Subject -eq $certificate.Issuer) { throw 'Self-signed certificates are not accepted for releases' }
if (-not ($certificate.EnhancedKeyUsageList.ObjectId -contains '1.3.6.1.5.5.7.3.3')) { throw 'Certificate is not enabled for code signing' }
$certificateName = $certificate.GetNameInfo([System.Security.Cryptography.X509Certificates.X509NameType]::SimpleName, $false)
if ($Publisher -ne $certificateName) { throw "Publisher must match certificate identity: $certificateName" }
$chain = New-Object System.Security.Cryptography.X509Certificates.X509Chain
$chain.ChainPolicy.RevocationMode = [System.Security.Cryptography.X509Certificates.X509RevocationMode]::Online
try {
    if (-not $chain.Build($certificate)) { throw 'Certificate trust/revocation validation failed' }
} finally { $chain.Dispose() }
if (-not $SignTool) {
    $candidate = Get-ChildItem "${env:ProgramFiles(x86)}\Windows Kits\10\bin\*\x64\signtool.exe" -ErrorAction SilentlyContinue |
                 Sort-Object FullName -Descending | Select-Object -First 1
    if (-not $candidate) { throw 'Install the Windows SDK signing tools or pass -SignTool' }
    $SignTool = $candidate.FullName
}
if (-not (Test-Path -LiteralPath $SignTool)) { throw 'SignTool not found' }
if ($CheckOnly) { Write-Host "Signing preflight passed for $certificateName"; exit 0 }
$target = (Resolve-Path -LiteralPath $FilePath).Path
& $SignTool sign /sha1 $CertificateThumbprint /s My /fd SHA256 /tr $TimestampUrl /td SHA256 /d EmailChronicle $target
if ($LASTEXITCODE -ne 0) { throw "Signing failed for $target" }
& $SignTool verify /pa /all /tw $target
if ($LASTEXITCODE -ne 0) { throw "Signature verification failed for $target" }
$signature = Get-AuthenticodeSignature -LiteralPath $target
if ($signature.Status -ne 'Valid' -or -not $signature.TimeStamperCertificate -or
    $signature.SignerCertificate.Thumbprint -ne $CertificateThumbprint) {
    throw "Trusted timestamped signature from the selected publisher missing: $target"
}
