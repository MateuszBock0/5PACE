@echo off
cd /d "%~dp0competitive-intelligence"
.venv\Scripts\python.exe sync.py --authorise
pause
