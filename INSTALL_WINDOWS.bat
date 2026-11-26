@echo off
setlocal
cd /d "%~dp0competitive-intelligence"
where py >nul 2>&1
if errorlevel 1 goto fail
if not exist .venv\Scripts\python.exe (
  py -3.12 -m venv .venv
  if errorlevel 1 py -3.11 -m venv .venv
  if errorlevel 1 goto fail
)
.venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 goto fail
if not exist config.local.json copy config.example.json config.local.json
if not exist credentials mkdir credentials
echo Installation complete. See README.md for OAuth setup.
pause
exit /b 0
:fail
echo Installation failed. Install Python 3.11 or 3.12 and check internet access.
pause
exit /b 1
