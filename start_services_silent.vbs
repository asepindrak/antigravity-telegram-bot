Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
currentDir = fso.GetParentFolderName(WScript.ScriptFullName)
WshShell.CurrentDirectory = currentDir

' Ensure logs directory exists
If Not fso.FolderExists(currentDir & "\logs") Then
    fso.CreateFolder(currentDir & "\logs")
End If

' 1. Check if AGY Bridge is already running on port 8001
checkBridgeCmd = "powershell.exe -NoProfile -ExecutionPolicy Bypass -Command " & chr(34) & "$c = Get-NetTCPConnection -LocalPort 8001 -ErrorAction SilentlyContinue; if ($c) { exit 10 } else { exit 20 }" & chr(34)
bridgeRet = WshShell.Run(checkBridgeCmd, 0, True)

If bridgeRet = 20 Then
    WshShell.Run "cmd.exe /c " & chr(34) & currentDir & "\run_bridge.bat" & chr(34), 0, False
End If

' 2. Check if Telegram Bot is already running
checkBotCmd = "powershell.exe -NoProfile -ExecutionPolicy Bypass -Command " & chr(34) & "$b = Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*telegram_bot.py*' -and $_.CommandLine -notlike '*Get-CimInstance*' }; if ($b) { exit 10 } else { exit 20 }" & chr(34)
botRet = WshShell.Run(checkBotCmd, 0, True)

If botRet = 20 Then
    WshShell.Run "cmd.exe /c " & chr(34) & currentDir & "\start_bot.bat" & chr(34), 0, False
End If

Set WshShell = Nothing
Set fso = Nothing
