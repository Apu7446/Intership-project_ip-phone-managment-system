Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
strAppDir = fso.GetAbsolutePathName(".")
strDesktop = WshShell.SpecialFolders("Desktop")

shortcutPath = strDesktop & "\SBAC IP Phone Management System.lnk"
If fso.FileExists(shortcutPath) Then
    On Error Resume Next
    fso.DeleteFile shortcutPath, True
    On Error GoTo 0
End If

Set objShortcut = WshShell.CreateShortcut(shortcutPath)
objShortcut.TargetPath = "wscript.exe"
objShortcut.Arguments = """" & strAppDir & "\launch.vbs"""
objShortcut.WorkingDirectory = strAppDir
objShortcut.Description = "SBAC Bank PLC — IP Phone Management System"
objShortcut.IconLocation = strAppDir & "\app_icon.ico,0"
objShortcut.Save

WScript.Echo "[OK] Desktop shortcut created on Bank PC with official SBAC Bank logo icon!"
