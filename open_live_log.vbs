Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)
command = "powershell -NoExit -ExecutionPolicy Bypass -File """ & scriptDir & "\watch_background_log.ps1"""
shell.Run command, 1, False
