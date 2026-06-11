' Dorita Dictado — Launcher silencioso (sin ventana negra).
' Doble click en este archivo o ponelo en shell:startup para arrancar con Windows.
Set sh = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
proyecto = fso.GetParentFolderName(WScript.ScriptFullName)
comando = """" & proyecto & "\.venv\Scripts\pythonw.exe"" """ & proyecto & "\dictado.py"""
sh.CurrentDirectory = proyecto
sh.Run comando, 0, False
