@echo off
title Smart File Organizer
cd /d "%~dp0"

set "PYTHON_EXE="
set "PYTHON_ARGS="

:: Check installed Python in User Local AppData
for %%V in (313 312 311 310) do (
    if exist "%LOCALAPPDATA%\Programs\Python\Python%%V\python.exe" (
        set "PYTHON_EXE=%LOCALAPPDATA%\Programs\Python\Python%%V\python.exe"
        goto found
    )
)

:: Check py launcher
where py >nul 2>&1
if %ERRORLEVEL% equ 0 (
    py -3 -c "import sys" >nul 2>&1
    if %ERRORLEVEL% equ 0 (
        set "PYTHON_EXE=py"
        set "PYTHON_ARGS=-3"
        goto found
    )
)

:: Check standard python
where python >nul 2>&1
if %ERRORLEVEL% equ 0 (
    python -c "import sys" >nul 2>&1
    if %ERRORLEVEL% equ 0 (
        set "PYTHON_EXE=python"
        goto found
    )
)

:: Check standard C:\Python* installations
for %%V in (313 312 311 310) do (
    if exist "C:\Python%%V\python.exe" (
        set "PYTHON_EXE=C:\Python%%V\python.exe"
        goto found
    )
)

echo [ERROR] Python was not found on your system!
echo Please make sure Python 3.10+ is installed.
pause
exit /b 1

:found
if defined PYTHON_ARGS (
    echo Starting Smart File Organizer using: "%PYTHON_EXE%" %PYTHON_ARGS%
    "%PYTHON_EXE%" %PYTHON_ARGS% main.py %*
) else (
    echo Starting Smart File Organizer using: "%PYTHON_EXE%"
    "%PYTHON_EXE%" main.py %*
)
if %ERRORLEVEL% neq 0 (
    echo.
    echo Application exited.
    pause
)
