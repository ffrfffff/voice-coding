Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)
command = "pythonw """ & scriptDir & "\desktop_app.py"""
shell.Run command, 0, False
