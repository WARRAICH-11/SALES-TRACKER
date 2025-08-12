#!/bin/bash

# Sales Tracker - Complete Build Script for Linux/macOS
# This script builds both the desktop app and prepares the cloud backend

set -e

echo ""
echo "========================================"
echo "   Sales Tracker - Complete Build"
echo "========================================"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    print_error "Python 3 is not installed or not in PATH"
    exit 1
fi

# Build Desktop Application
print_status "[1/3] Building Desktop Application..."
echo ""
cd py-sales-tracker

# Create virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
    print_status "Creating virtual environment..."
    python3 -m venv .venv
fi

# Activate virtual environment
source .venv/bin/activate

# Install dependencies
print_status "Installing dependencies..."
pip install -r requirements.txt
pip install pyinstaller

# Build executable
print_status "Building executable with PyInstaller..."
pyinstaller --noconfirm --noconsole --name SalesTracker \
    --add-data "app:app" \
    --add-data "models:models" \
    --hidden-import "app.widgets.dashboard" \
    --hidden-import "app.widgets.sales_entry" \
    --hidden-import "app.widgets.customers" \
    --hidden-import "app.widgets.inventory" \
    --hidden-import "app.widgets.ai_insights" \
    --hidden-import "app.ai.rag" \
    --hidden-import "app.ai.forecast" \
    --hidden-import "sentence_transformers" \
    --hidden-import "faiss" \
    --hidden-import "plotly" \
    app/main.py

print_status "Desktop app built successfully!"
print_status "Location: py-sales-tracker/dist/SalesTracker/"
echo ""

# Go back to root
cd ..

# Prepare Cloud Backend
print_status "[2/3] Preparing Cloud Backend..."
echo ""
cd cloud-backend

# Create .env if it doesn't exist
if [ ! -f ".env" ]; then
    print_status "Creating default .env file..."
    cp .env.example .env
    print_warning "Please update .env with production values!"
fi

# Test backend dependencies
print_status "Testing backend dependencies..."
python3 -c "import fastapi, uvicorn, sqlalchemy; print('All backend dependencies available')" || {
    print_status "Installing backend dependencies..."
    pip install -r requirements.txt
}

print_status "Backend prepared successfully!"
echo ""

cd ..

# Create distribution package
print_status "[3/3] Creating Distribution Package..."
echo ""

# Create build directory
if [ -d "build-output" ]; then
    rm -rf "build-output"
fi
mkdir -p "build-output"

# Copy desktop app
print_status "Copying desktop application..."
cp -r "py-sales-tracker/dist/SalesTracker" "build-output/"

# Copy cloud backend
print_status "Copying cloud backend..."
rsync -av --exclude-from=build_exclude.txt "cloud-backend/" "build-output/cloud-backend/"

# Copy documentation and scripts
cp README.md "build-output/" 2>/dev/null || true
cp DEPLOYMENT.md "build-output/"
cp deploy_docker.sh "build-output/"
cp build_win.bat "build-output/"
cp build_mac.sh "build-output/"
cp build_linux.sh "build-output/"
cp build_all.sh "build-output/"
cp build_all.bat "build-output/"

# Make scripts executable
chmod +x "build-output/deploy_docker.sh"
chmod +x "build-output/build_mac.sh"
chmod +x "build-output/build_linux.sh"
chmod +x "build-output/build_all.sh"

# Create build info
print_status "Creating build information..."
cat > "build-output/BUILD_INFO.txt" << EOF
Build Date: $(date)
Built on: $(hostname)
OS: $(uname -s)
Python Version: $(python3 --version)
EOF

echo ""
echo "========================================"
echo "           BUILD COMPLETED!"
echo "========================================"
echo ""
echo "Desktop App: build-output/SalesTracker/SalesTracker"
echo "Cloud Backend: build-output/cloud-backend/"
echo "Documentation: build-output/DEPLOYMENT.md"
echo ""
echo "Next steps:"
echo "1. Test the desktop application"
echo "2. Configure cloud backend .env file"
echo "3. Deploy using Docker or direct Python"
echo "4. Distribute the build-output folder"
echo ""
