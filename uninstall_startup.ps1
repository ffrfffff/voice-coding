$startup = [Environment]::GetFolderPath("Startup")
$items = @(
  (Join-Path $startup "Voice Agent F7 F8.lnk"),
  (Join-Path $startup "Voice Agent Log.lnk")
)

foreach ($item in $items) {
  if (Test-Path $item) {
    Remove-Item -LiteralPath $item -Force
    Write-Host "Removed $item"
  }
}
