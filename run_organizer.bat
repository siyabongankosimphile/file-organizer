@echo off
title Smart File Organizer
cd /d "%~dp0"

set PYTHON_CMD=

:: Check installed Python 3.11 in User Local AppData
if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" (
    set "PYTHON_CMD=%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
    goto found
)

:: Check py launcher
where py >nul 2>&1
if %ERRORLEVEL% equ 0 (
    py -3 -c "import sys" >nul 2>&1
    if %ERRORLEVEL% equ 0 (
        set "PYTHON_CMD=py -3"
        goto found
    )
)

:: Check standard python
where python >nul 2>&1
if %ERRORLEVEL% equ 0 (
    python -c "import sys" >nul 2>&1
    if %ERRORLEVEL% equ 0 (
        set "PYTHON_CMD=python"
        goto found
    )
)

:: Check Python314 / standard C:\Python*
if exist "C:\Python311\python.exe" set "PYTHON_CMD=C:\Python311\python.exe" & goto found
if exist "C:\Python312\python.exe" set "PYTHON_CMD=C:\Python312\python.exe" & goto found
if exist "C:\Python310\python.exe" set "PYTHON_CMD=C:\Python310\python.exe" & goto found

echo [ERROR] Python was not found on your system!
echo Please make sure Python is installed.
pause
exit /b 1

:found
echo Starting Smart File Organizer using: %PYTHON_CMD%
%PYTHON_CMD% main.py %*
if %ERRORLEVEL% neq 0 (
    echo.
    echo Application exited.
    pause
)
