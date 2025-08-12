@echo off
REM Sales Tracker - Complete Build Script for Windows
REM This script builds both the desktop app and prepares the cloud backend

echo.
echo ========================================
echo   Sales Tracker - Complete Build
echo ========================================
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    pause
    exit /b 1
)

REM Build Desktop Application
echo [1/3] Building Desktop Application...
echo.
cd py-sales-tracker

REM Create virtual environment if it doesn't exist
if not exist ".venv" (
    echo Creating virtual environment...
    python -m venv .venv
)

REM Activate virtual environment
call .venv\Scripts\activate.bat

REM Install dependencies
echo Installing dependencies...
pip install -r requirements.txt
pip install pyinstaller

REM Build executable
echo Building executable with PyInstaller...
pyinstaller --noconfirm --noconsole --name SalesTracker ^
    --add-data "app;app" ^
    --add-data "models;models" ^
    --hidden-import "app.widgets.dashboard" ^
    --hidden-import "app.widgets.sales_entry" ^
    --hidden-import "app.widgets.customers" ^
    --hidden-import "app.widgets.inventory" ^
    --hidden-import "app.widgets.ai_insights" ^
    --hidden-import "app.ai.rag" ^
    --hidden-import "app.ai.forecast" ^
    --hidden-import "sentence_transformers" ^
    --hidden-import "faiss" ^
    --hidden-import "plotly" ^
    app/main.py

if errorlevel 1 (
    echo ERROR: Build failed
    pause
    exit /b 1
)

echo Desktop app built successfully!
echo Location: py-sales-tracker\dist\SalesTracker\
echo.

REM Go back to root
cd ..

REM Prepare Cloud Backend
echo [2/3] Preparing Cloud Backend...
echo.
cd cloud-backend

REM Create .env if it doesn't exist
if not exist ".env" (
    echo Creating default .env file...
    copy .env.example .env
    echo WARNING: Please update .env with production values!
)

REM Test backend dependencies
echo Testing backend dependencies...
python -c "import fastapi, uvicorn, sqlalchemy; print('All backend dependencies available')"
if errorlevel 1 (
    echo Installing backend dependencies...
    pip install -r requirements.txt
)

echo Backend prepared successfully!
echo.

cd ..

REM Create distribution package
echo [3/3] Creating Distribution Package...
echo.

REM Create build directory
if exist "build-output" rmdir /s /q "build-output"
mkdir "build-output"

REM Copy desktop app
echo Copying desktop application...
xcopy "py-sales-tracker\dist\SalesTracker" "build-output\SalesTracker\" /E /I /H /Y

REM Copy cloud backend
echo Copying cloud backend...
xcopy "cloud-backend" "build-output\cloud-backend\" /E /I /H /Y /EXCLUDE:build_exclude.txt

REM Copy documentation and scripts
copy "README.md" "build-output\" 2>nul
copy "DEPLOYMENT.md" "build-output\"
copy "deploy_docker.sh" "build-output\"
copy "build_win.bat" "build-output\"
copy "build_mac.sh" "build-output\"
copy "build_linux.sh" "build-output\"

REM Create build info
echo Creating build information...
echo Build Date: %date% %time% > "build-output\BUILD_INFO.txt"
echo Built on: %computername% >> "build-output\BUILD_INFO.txt"
echo Python Version: >> "build-output\BUILD_INFO.txt"
python --version >> "build-output\BUILD_INFO.txt"

echo.
echo ========================================
echo           BUILD COMPLETED!
echo ========================================
echo.
echo Desktop App: build-output\SalesTracker\SalesTracker.exe
echo Cloud Backend: build-output\cloud-backend\
echo Documentation: build-output\DEPLOYMENT.md
echo.
echo Next steps:
echo 1. Test the desktop application
echo 2. Configure cloud backend .env file
echo 3. Deploy using Docker or direct Python
echo 4. Distribute the build-output folder
echo.
pause
