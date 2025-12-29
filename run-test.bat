@echo off

set HTTPS_PROXY=http://127.0.0.1:10808

call uv run test.py
pause