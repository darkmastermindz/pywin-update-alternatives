@echo off
setlocal

rem -----------------------------------------------------------------------
rem pywin-update-alternatives.cmd
rem Works in CMD Prompt and Git Bash (via cmd.exe invocation).
rem First tries to delegate to the PowerShell bootstrap for the embedded
rem Python runtime; if PowerShell is unavailable or execution policy blocks
rem it, falls back to a Python interpreter already on PATH.
rem -----------------------------------------------------------------------

rem Check whether PowerShell is accessible
where powershell >nul 2>&1
if %ERRORLEVEL% neq 0 goto :fallback_python

rem Try the PowerShell bootstrap
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\pywin-update-alternatives.ps1" %*
if %ERRORLEVEL% equ 0 goto :eof
rem If PowerShell script failed (e.g. network policy), fall through to Python fallback

:fallback_python
if defined PYWIN_UPDATE_ALTERNATIVES_PYTHON (
    "%PYWIN_UPDATE_ALTERNATIVES_PYTHON%" -m pywin_update_alternatives %*
    exit /b %ERRORLEVEL%
)

rem Try the embedded Python runtime first
if exist "%~dp0.embedded-python\python.exe" (
    "%~dp0.embedded-python\python.exe" -m pywin_update_alternatives %*
    exit /b %ERRORLEVEL%
)

rem Try system Python launchers in order of preference
for %%P in (python py python3) do (
    where %%P >nul 2>&1
    if not errorlevel 1 (
        %%P -m pywin_update_alternatives %*
        exit /b %ERRORLEVEL%
    )
)

echo Error: Python 3.7+ not found. Please install Python or run the PowerShell
echo        bootstrap first: scripts\pywin-update-alternatives.ps1
exit /b 1
