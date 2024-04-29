@echo off

set http_proxy=http://127.0.0.1:10809
set https_proxy=http://127.0.0.1:10809

call %cd%\\venv\\scripts\\python.exe test.py


pause