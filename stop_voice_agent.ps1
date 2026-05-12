$connections = Get-NetTCPConnection -LocalPort 8765 -State Listen -ErrorAction SilentlyContinue
if ($connections) {
  $connections | Select-Object -ExpandProperty OwningProcess | Sort-Object -Unique | ForEach-Object {
    $p = Get-Process -Id $_ -ErrorAction SilentlyContinue
    if ($p -and $p.ProcessName -like 'python*') {
      Stop-Process -Id $_ -Force
      Write-Host "Stopped Voice Agent process $_"
    }
  }
}

Get-CimInstance Win32_Process |
  Where-Object {
    $_.Name -like 'python*' -and
    $_.CommandLine -match 'background_voice_agent.py|desktop_app.py|web_app.py|app.py'
  } |
  ForEach-Object {
    Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
    Write-Host "Stopped Voice Agent process $($_.ProcessId)"
  }
