$ErrorActionPreference = "Stop"
$startup = [Environment]::GetFolderPath("Startup")
$repo = $PSScriptRoot

$agentShortcut = Join-Path $startup "Voice Agent F7 F8.lnk"
$logShortcut = Join-Path $startup "Voice Agent Log.lnk"

$shell = New-Object -ComObject WScript.Shell

$agent = $shell.CreateShortcut($agentShortcut)
$agent.TargetPath = "wscript.exe"
$agent.Arguments = "`"$repo\start_f8_voice_agent.vbs`""
$agent.WorkingDirectory = $repo
$agent.WindowStyle = 7
$agent.Description = "Start background F7/F8 voice agent and tray control panel"
$agent.Save()

if (Test-Path $logShortcut) {
  Remove-Item -LiteralPath $logShortcut -Force
}

Write-Host "Installed startup shortcut:"
Write-Host $agentShortcut
