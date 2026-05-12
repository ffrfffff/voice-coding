Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
Set wmi = GetObject("winmgmts:\\.\root\cimv2")

scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)

If Not IsRunning(wmi, "background_voice_agent.py") Then
  command = "pythonw """ & scriptDir & "\background_voice_agent.py"""
  shell.Run command, 0, False
End If

If Not IsRunning(wmi, "log_overlay.py") Then
  logCommand = "pythonw """ & scriptDir & "\log_overlay.py"""
  shell.Run logCommand, 0, False
End If

Function IsRunning(wmi, scriptName)
  IsRunning = False
  query = "SELECT CommandLine FROM Win32_Process WHERE Name LIKE 'python%'"
  For Each process In wmi.ExecQuery(query)
    If Not IsNull(process.CommandLine) Then
      If InStr(1, process.CommandLine, scriptName, vbTextCompare) > 0 Then
        IsRunning = True
        Exit Function
      End If
    End If
  Next
End Function
