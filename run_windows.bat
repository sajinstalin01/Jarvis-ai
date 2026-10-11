@echo off
setlocal
cd /d "%~dp0"
if not exist .venv (
  py -m venv .venv
  if errorlevel 1 goto error
)
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt
if not exist .env copy .env.example .env
where git >nul 2>nul
if %errorlevel%==0 if exist .git (
  echo Checking GitHub for JARVIS updates...
  python auto_update.py
  echo.
)
python jarvis_v2.py
pause
exit /b 0
:error
echo Python launcher not found. Install Python 3.10+ and enable Add Python to PATH.
pause
exit /b 1
