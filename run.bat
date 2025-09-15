@REM @echo off
@REM call %cd%\\venv\\scripts\\python.exe sp.py

@REM pause

@REM @echo off
@REM REM %~dp0 会自动获取bat文件所在的目录，这比%cd%更可靠
@REM call "%~dp0venv\scripts\python.exe" "%~dp0sp.py"
@REM pause

@REM @echo off
@REM REM 设置代码页为UTF-8，防止中文乱码
@REM chcp 65001 > nul

@REM echo.
@REM echo 准备使用 Conda 环境运行 Python 脚本 (已开启实时输出)...
@REM echo.

@REM REM 在 python 后面加上 -u 参数来禁用输出缓冲
@REM conda run --prefix "%~dp0venv" python -u -X utf8 "%~dp0sp.py"

@REM echo.
@REM echo 脚本运行结束。
@REM pause

@echo off
echo ======================================
echo   PVT Runtime Boot Start
echo ======================================

:: 1. 设置路径（改为使用脚本所在目录）
SET ROOT=%~dp0
SET ENV=%ROOT%\venv
SET PYTHON=%ENV%\python.exe


:: 2. 清理环境变量，避免冲突
SET PYTHONHOME=
SET PYTHONPATH=
SET PYTHONEXECUTABLE=



:: 4. 启动程序
echo Launching: webui.py
"%PYTHON%" -s "%ROOT%sp.py" %*

:: 5. 运行完毕提示
echo.
echo Done.
pause