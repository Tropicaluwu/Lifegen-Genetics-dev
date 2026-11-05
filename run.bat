@echo off

:: start in this file's folder, even when run as administrator or from a shortcut
cd /d "%~dp0"

uv sync || ( pause & exit /b )
uv run main.py || ( pause & exit /b )