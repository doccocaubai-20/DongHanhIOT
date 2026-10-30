@echo off
cd /d "%~dp0"
set PYTHONUTF8=1
if not exist .venv\Scripts\python.exe py -3.12 -m venv .venv
if errorlevel 1 goto error
.venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 goto error
rem Thu vien AI ban CPU cho SegFormer (chi tai o lan dau, khoang vai tram MB).
.venv\Scripts\python.exe -c "import torch, torchvision, transformers" 2>nul
if errorlevel 1 (
  .venv\Scripts\python.exe -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
  .venv\Scripts\python.exe -m pip install -r ai\requirements-ai.txt
)
.venv\Scripts\python.exe scripts\setup.py
if errorlevel 1 goto error
echo Dia chi IPv4 cua may nay (ESP32 dung http://IPv4:8000 lam API_BASE):
ipconfig | findstr /c:"IPv4"
echo Mo http://localhost:8000 tren trinh duyet.
.venv\Scripts\python.exe -m uvicorn server.app:app --host 0.0.0.0 --port 8000 --workers 1
:error
pause
