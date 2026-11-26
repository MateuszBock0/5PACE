@echo off
setlocal
cd /d "%~dp0competitive-intelligence"
if not exist .venv\Scripts\python.exe (
  echo Run INSTALL_WINDOWS.bat first.
  pause
  exit /b 1
)
start "CIE synchronisation" /min .venv\Scripts\python.exe sync.py --if-stale
.venv\Scripts\python.exe -m streamlit run app.py
