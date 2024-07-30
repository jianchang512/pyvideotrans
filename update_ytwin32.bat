@echo off
setlocal

:: Calls the Python script and keeps the window open
python "%~dp0videotrans\task\update_ytdlp.py"
pause

endlocal
