@echo off
cd /d "C:\Users\IVAN LAFUENTE\Projects\dorita-dictado"
if not exist .venv (
    echo Creando entorno virtual por primera vez...
    python -m venv .venv
    call .venv\Scripts\activate.bat
    pip install -r requirements.txt
) else (
    call .venv\Scripts\activate.bat
)
python dictado.py
pause
