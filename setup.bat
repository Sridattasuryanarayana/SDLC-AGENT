@echo off
REM Quick Start Script for SDLC Agent (Windows)
REM Run this to get up and running quickly

echo.
echo 🚀 SDLC Agent - Quick Start Setup
echo ==================================
echo.

REM Check Python
echo ✓ Checking Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python not found. Please install Python 3.8+
    exit /b 1
)

for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo    Python %PYTHON_VERSION% found
echo.

REM Create virtual environment
echo ✓ Creating virtual environment...
if not exist "venv" (
    python -m venv venv
    echo    Virtual environment created
) else (
    echo    Virtual environment already exists
)
echo.

REM Activate virtual environment
echo ✓ Activating virtual environment...
call venv\Scripts\activate.bat
echo    Activated
echo.

REM Install dependencies
echo ✓ Installing dependencies...
pip install --quiet -r requirements.txt
echo    Dependencies installed
echo.

REM Create .env file
echo ✓ Setting up configuration...
if not exist ".env" (
    copy .env.example .env
    echo    Created .env ^(update with your API keys^)
) else (
    echo    .env already exists
)
echo.

REM Create directories
echo ✓ Creating directories...
if not exist "output" mkdir output
if not exist "uploads" mkdir uploads
if not exist "tasks" mkdir tasks
echo    Directories created
echo.

echo ✅ Setup Complete!
echo.
echo Next steps:
echo 1. Edit .env with your API keys
echo 2. Add tasks to tasks/development_tasks.xlsx
echo 3. Start task watcher: python task_watcher.py
echo 4. Or start web interface: python web_app.py
echo.
echo For more info, see README.md or WORKFLOW_GUIDE.md
