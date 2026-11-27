@echo off
cd /d "%~dp0competitive-intelligence"
.venv\Scripts\python.exe scripts\live_acceptance.py
pause
