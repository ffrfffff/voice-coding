Set-Location -LiteralPath $PSScriptRoot
$log = Join-Path $PSScriptRoot "data\logs\background.log"
if (!(Test-Path $log)) {
  New-Item -ItemType File -Path $log -Force | Out-Null
}
Clear-Host
Write-Host "Voice Agent live log"
Write-Host "F8 start/stop recording. Esc stops speech. Ctrl+C closes this log window."
Write-Host ""
Get-Content -LiteralPath $log -Wait -Tail 40 -Encoding UTF8
