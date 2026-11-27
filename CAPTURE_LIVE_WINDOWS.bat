@echo off
cd /d "%~dp0competitive-intelligence"
.venv\Scripts\python.exe -m pip install playwright
if errorlevel 1 goto end
.venv\Scripts\python.exe -m playwright install chromium
if errorlevel 1 goto end
.venv\Scripts\python.exe scripts\capture_ux.py reports\live-screenshots --live
:end
pause
