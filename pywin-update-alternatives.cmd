@echo off
setlocal
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\pywin-update-alternatives.ps1" %*
exit /b %ERRORLEVEL%
