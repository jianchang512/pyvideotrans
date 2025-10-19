@echo off

cd dist\docs
rem set https_proxy=http://127.0.0.1:10808
call F:\python\pyvideo\venv\scripts\python.exe F:\python\pyvideo\dist\docs\_gemini.py
pause