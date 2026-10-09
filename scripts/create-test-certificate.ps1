param()
$ErrorActionPreference = 'Stop'
# This identity is deliberately not a legal publisher identity or a trusted root.
$subject = 'CN=EmailChronicle LOCAL TEST ONLY'
$friendlyName = 'EmailChronicle local development signing (TEST ONLY)'
$certificate = Get-ChildItem Cert:\CurrentUser\My | Where-Object {
    $_.Subject -eq $subject -and $_.FriendlyName -eq $friendlyName -and
    $_.HasPrivateKey -and $_.NotAfter -gt (Get-Date).AddDays(1) -and
    $_.EnhancedKeyUsageList.ObjectId -contains '1.3.6.1.5.5.7.3.3'
} | Sort-Object NotAfter -Descending | Select-Object -First 1
if (-not $certificate) {
    $certificate = New-SelfSignedCertificate -Type CodeSigningCert `
        -Subject $subject -FriendlyName $friendlyName `
        -CertStoreLocation Cert:\CurrentUser\My `
        -Provider 'Microsoft Software Key Storage Provider' `
        -KeyAlgorithm RSA -KeyLength 3072 -HashAlgorithm SHA256 `
        -KeyExportPolicy NonExportable -NotAfter (Get-Date).AddDays(90)
}
$outputDirectory = Join-Path (Split-Path $PSScriptRoot -Parent) '.local-signing'
New-Item -ItemType Directory -Path $outputDirectory -Force | Out-Null
Export-Certificate -Cert $certificate -FilePath (Join-Path $outputDirectory 'EmailChronicle-TEST-ONLY.cer') -Force | Out-Null
$probePath = Join-Path $outputDirectory 'signature-probe.ps1'
Set-Content -LiteralPath $probePath -Value "Write-Output 'EmailChronicle signing probe; no evidence accessed.'" -Encoding Unicode
$signature = Set-AuthenticodeSignature -FilePath $probePath -Certificate $certificate -HashAlgorithm SHA256
if (-not $signature.SignerCertificate -or $signature.SignerCertificate.Thumbprint -ne $certificate.Thumbprint) {
    throw 'The signing probe did not receive the expected signature'
}
$tamperedPath = Join-Path $outputDirectory 'signature-probe-tampered.ps1'
$probeText = Get-Content -LiteralPath $probePath -Raw
$probeText.Replace('no evidence accessed.', 'deliberately changed content.') | Set-Content -LiteralPath $tamperedPath -Encoding Unicode
$tamperedSignature = Get-AuthenticodeSignature -FilePath $tamperedPath
if ($tamperedSignature.Status -notin @('HashMismatch', 'NotSigned')) {
    throw "Changed probe was not rejected as expected: $($tamperedSignature.Status)"
}
$metadata = [ordered]@{
    test_only = $true
    subject = $certificate.Subject
    thumbprint = $certificate.Thumbprint
    expires_utc = $certificate.NotAfter.ToUniversalTime().ToString('o')
    store = 'Cert:\CurrentUser\My'
    private_key_exported = $false
    trusted_root_installed = $false
    probe_signature_status = [string]$signature.Status
    tampered_probe_status = [string]$tamperedSignature.Status
}
$metadata | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $outputDirectory 'test-certificate.json') -Encoding Unicode
$metadata | ConvertTo-Json
Write-Host 'TEST ONLY: this does not establish a trusted publisher. Release signing rejects self-signed certificates.'

