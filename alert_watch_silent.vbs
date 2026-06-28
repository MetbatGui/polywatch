Set WshShell = CreateObject("WScript.Shell")
projDir = "C:\Users\Zeya\Develop\Projects\polywatch"
uvExe = "C:\Users\Zeya\.local\bin\uv.exe"

WshShell.Run "cmd /c cd /d """ & projDir & """ && """ & uvExe & """ run python -m src.runner", 0, False
