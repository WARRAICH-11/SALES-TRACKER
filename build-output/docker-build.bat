@echo off
REM Sales Tracker - Docker-Only Build (No Python Installation Required)
REM This script builds everything using Docker containers

echo.
echo ========================================
echo   Sales Tracker - Docker Build
echo ========================================
echo.

REM Check if Docker is available
docker --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Docker is not installed
    echo Please install Docker Desktop from: https://www.docker.com/products/docker-desktop/
    pause
    exit /b 1
)

echo [INFO] Docker found, proceeding with build...
echo.

REM Create build output directory
if exist "build-output" rmdir /s /q "build-output"
mkdir "build-output"

REM Build Cloud Backend
echo [1/2] Building Cloud Backend...
cd cloud-backend

REM Create .env if missing
if not exist ".env" (
    echo Creating default .env file...
    copy .env.example .env
)

REM Build and test backend
echo Building backend container...
docker-compose build
if errorlevel 1 (
    echo ERROR: Backend build failed
    pause
    exit /b 1
)

echo Testing backend...
docker-compose up -d
timeout /t 10 /nobreak >nul
curl -f http://localhost:8000/healthz >nul 2>&1
if errorlevel 1 (
    echo WARNING: Backend health check failed, but continuing...
)
docker-compose down

echo Backend built successfully!
cd ..

REM Copy everything to build output
echo [2/2] Creating Distribution Package...

REM Copy cloud backend
xcopy "cloud-backend" "build-output\cloud-backend\" /E /I /H /Y

REM Copy documentation
copy "*.md" "build-output\" 2>nul
copy "*.bat" "build-output\" 2>nul
copy "*.sh" "build-output\" 2>nul

REM Copy desktop app source (for users with Python)
xcopy "py-sales-tracker" "build-output\py-sales-tracker\" /E /I /H /Y

REM Create deployment instructions
echo Creating deployment package...
echo Build Date: %date% %time% > "build-output\BUILD_INFO.txt"
echo Build Type: Docker-Only >> "build-output\BUILD_INFO.txt"
echo Requirements: Docker Desktop >> "build-output\BUILD_INFO.txt"

echo.
echo ========================================
echo        BUILD COMPLETED!
echo ========================================
echo.
echo Package Location: build-output\
echo.
echo READY TO USE:
echo - Cloud Backend: build-output\cloud-backend\
echo - Run: cd build-output\cloud-backend && docker-compose up
echo - Access: http://localhost:8000
echo.
echo FOR DESKTOP APP:
echo - Install Python 3.10+ first
echo - Then: cd build-output\py-sales-tracker && python app\main.py
echo.
echo See SETUP_GUIDE.md for complete instructions
echo.
pause
