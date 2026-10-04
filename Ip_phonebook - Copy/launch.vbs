Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
strAppDir = fso.GetParentFolderName(WScript.ScriptFullName)
WshShell.CurrentDirectory = strAppDir
WshShell.Run "cmd /c RUN_APP.bat", 0, False

