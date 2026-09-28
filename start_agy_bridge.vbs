Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = "C:\Users\sangp\learn-with-runa"
WshShell.Run chr(34) & "C:\Users\sangp\learn-with-runa\run_bridge.bat" & chr(34), 0
Set WshShell = Nothing
