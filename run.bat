@echo off
REM run.bat — double-click launcher (Windows). Starts the example AI-vs-AI match
REM and opens the board. No typing required. Press Start on the page to begin.
cd /d "%~dp0"

REM let the clients bind their ports
timeout /t 1 /nobreak >nul

REM the engine — serves the board and drives the AIs
start "engine" python server.py

REM open the board once the server is up
timeout /t 2 /nobreak >nul
start "" http://127.0.0.1:5050/