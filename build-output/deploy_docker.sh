#!/bin/bash

# Sales Tracker - Docker Deployment Script
# This script builds and deploys both the desktop app and cloud backend using Docker

set -e

echo "🚀 Sales Tracker Docker Deployment"
echo "=================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    print_error "Docker is not installed. Please install Docker first."
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    print_error "Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

# Check if we're in the right directory
if [ ! -d "cloud-backend" ] || [ ! -d "py-sales-tracker" ]; then
    print_error "Please run this script from the project root directory."
    exit 1
fi

print_status "Deploying Cloud Backend..."

# Navigate to cloud-backend directory
cd cloud-backend

# Check if .env file exists
if [ ! -f ".env" ]; then
    print_warning ".env file not found. Creating default .env file..."
    cat > .env << EOF
SECRET_KEY=change-this-super-secret-key-in-production
SYNC_AES_KEY_BASE64=$(python3 -c "import os,base64;print(base64.b64encode(os.urandom(32)).decode())")
ADMIN_USER=admin
ADMIN_PASS=admin123
EOF
    print_warning "Default .env created. Please update with production values!"
fi

# Build and start the backend
print_status "Building and starting cloud backend..."
docker-compose down --remove-orphans
docker-compose up --build -d

# Wait for backend to be ready
print_status "Waiting for backend to be ready..."
sleep 10

# Check if backend is running
if curl -f http://localhost:8000/healthz > /dev/null 2>&1; then
    print_status "✅ Cloud backend is running at http://localhost:8000"
    print_status "✅ Admin dashboard available at http://localhost:8000/admin"
else
    print_error "❌ Backend failed to start properly"
    docker-compose logs
    exit 1
fi

# Go back to project root
cd ..

print_status "🎉 Deployment completed successfully!"
echo ""
echo "📋 Next Steps:"
echo "1. Update .env file in cloud-backend/ with production values"
echo "2. Build desktop app using build scripts (build_win.bat, build_mac.sh, build_linux.sh)"
echo "3. Configure desktop app to connect to http://localhost:8000"
echo ""
echo "🔗 Useful URLs:"
echo "   - API Health: http://localhost:8000/healthz"
echo "   - Admin Dashboard: http://localhost:8000/admin"
echo "   - API Documentation: http://localhost:8000/docs"
echo ""
echo "📊 To view logs: cd cloud-backend && docker-compose logs -f"
echo "🛑 To stop: cd cloud-backend && docker-compose down"