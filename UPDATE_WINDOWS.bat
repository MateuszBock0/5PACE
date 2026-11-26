@echo off
setlocal
cd /d "%~dp0"
where git >nul 2>&1
if errorlevel 1 goto fail
git rev-parse --is-inside-work-tree >nul 2>&1
if errorlevel 1 goto fail
for /f "delims=" %%i in ('git status --porcelain --untracked-files^=normal') do (
  echo Working tree is not clean. Commit or move local changes before updating.
  pause
  exit /b 1
)
git pull --ff-only
if errorlevel 1 goto fail
if not exist competitive-intelligence\.venv\Scripts\python.exe (
  call INSTALL_WINDOWS.bat
  exit /b
)
competitive-intelligence\.venv\Scripts\python.exe -m pip install -r competitive-intelligence\requirements.txt
if errorlevel 1 goto fail
echo Code and dependencies updated. Local intelligence, snapshots and credentials retained.
pause
exit /b 0
:fail
echo Update failed. No reset or clean has been performed. Check Git and network connectivity.
pause
exit /b 1
