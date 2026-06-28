Set WshShell = CreateObject("WScript.Shell")
projDir = "C:\Users\Zeya\Develop\Projects\polywatch"
uvExe = "C:\Users\Zeya\.local\bin\uv.exe"

Do
    WshShell.Run "cmd /c cd /d """ & projDir & """ && """ & uvExe & """ run python alert_watch.py", 0, True
    WScript.Sleep 10000
Loop
