@echo off
rem Launch JARVIS (Windows). Examples: jarvis.bat   jarvis.bat web   jarvis.bat voice
setlocal
set "HERE=%~dp0"
if exist "%HERE%.venv\Scripts\python.exe" (
  "%HERE%.venv\Scripts\python.exe" -m jarvis %*
) else (
  pushd "%HERE%"
  python -m jarvis %*
  popd
)
if errorlevel 1 pause
