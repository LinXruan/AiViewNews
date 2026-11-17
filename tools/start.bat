@echo off
setlocal
cd /d "%~dp0.."

set "PY=D:\Install\anaconda3\envs\deepseek\python.exe"
if not exist "%PY%" (
    where python >nul 2>nul
    if errorlevel 1 (
        echo [AiViewNews] Python not found.
        echo Please edit tools\start.bat and set the Python path.
        pause
        exit /b 1
    )
    set "PY=python"
)

if not exist "app\main.py" (
    echo [AiViewNews] app\main.py not found.
    echo Please run this script from the project folder.
    pause
    exit /b 1
)

echo [AiViewNews] Starting server at http://127.0.0.1:8000 ...
start "AiViewNews Server" cmd /k ""%PY%" -m uvicorn app.main:app --host 127.0.0.1 --port 8000"

"%SystemRoot%\System32\ping.exe" -n 4 127.0.0.1 >nul
start "" "http://127.0.0.1:8000"
endlocal
