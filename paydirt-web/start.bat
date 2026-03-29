@echo off
REM Paydirt Web - Start Script for Windows

echo Starting Paydirt Web...

REM Get the directory of this script
set "SCRIPT_DIR=%~dp0"
set "BACKEND_DIR=%SCRIPT_DIR%backend"
set "FRONTEND_DIR=%SCRIPT_DIR%frontend"

REM Start backend in a new window
echo Starting backend server on port 8000...
start "Paydirt Backend" cmd /k "cd /d "%BACKEND_DIR%" && python -m uvicorn main:app --reload --port 8000"

REM Wait a moment for backend to start
timeout /t 2 /nobreak >nul

REM Start frontend in a new window
echo Starting frontend dev server on port 5173...
start "Paydirt Frontend" cmd /k "cd /d "%FRONTEND_DIR%" && npm run dev"

echo.
echo ==============================================
echo   Paydirt Web is running!
echo.
echo   Frontend: http://localhost:5173
echo   Backend:  http://localhost:8000
echo.
echo   Close the command windows to stop
echo ==============================================
echo.

REM Exit this script (the servers are running in their own windows)
exit /b 0
