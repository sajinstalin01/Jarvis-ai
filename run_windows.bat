@echo off
setlocal
cd /d "%~dp0"

where py >nul 2>nul
if errorlevel 1 (
  where python >nul 2>nul
  if errorlevel 1 goto python_error
  set "PYTHON_CMD=python"
) else (
  set "PYTHON_CMD=py"
)

if not exist .venv (
  %PYTHON_CMD% -m venv .venv
  if errorlevel 1 goto error
)
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
if errorlevel 1 echo Warning: pip upgrade failed; continuing...
pip install -r requirements.txt
if errorlevel 1 echo Warning: dependency installation failed; check the output above.

if not exist .env if exist .env.example copy .env.example .env

if exist .git (
  echo.
  echo Checking GitHub for JARVIS updates using update_config.json...
  python auto_update.py
  if errorlevel 1 echo Update was skipped or failed. JARVIS will still start.
  echo.
) else (
  echo This folder is not a Git checkout. GitHub auto-update is unavailable.
)

python jarvis.py
pause
exit /b 0

:python_error
echo Python was not found. Install Python 3.10+ and enable Add Python to PATH.
pause
exit /b 1

:error
echo Could not create the virtual environment. Check your Python installation.
pause
exit /b 1
