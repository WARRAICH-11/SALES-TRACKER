# Sales Tracker - Production Build Guide

This document provides instructions for building and deploying the complete Sales Tracker application.

## Quick Start

### Windows
```bash
# Run the complete build
build_all.bat

# Or build individually
cd py-sales-tracker && build_win.bat
cd cloud-backend && docker-compose up --build
```

### Linux/macOS
```bash
# Make scripts executable
chmod +x build_all.sh deploy_docker.sh

# Run the complete build
./build_all.sh

# Or build individually
cd py-sales-tracker && ./build_linux.sh  # or ./build_mac.sh
cd cloud-backend && docker-compose up --build
```

## Build Output Structure

After running the build scripts, you'll find:

```
build-output/
├── SalesTracker/              # Desktop application executable
│   ├── SalesTracker.exe       # Windows executable
│   ├── SalesTracker           # Linux/macOS executable
│   └── _internal/             # Application dependencies
├── cloud-backend/             # Backend API service
│   ├── app/                   # FastAPI application
│   ├── Dockerfile             # Container configuration
│   ├── docker-compose.yml     # Docker orchestration
│   └── .env.example           # Environment template
├── DEPLOYMENT.md              # Deployment instructions
├── BUILD_INFO.txt             # Build metadata
└── build scripts...
```

## Pre-Build Requirements

### Desktop Application
- Python 3.10+
- PySide6 dependencies (automatically installed)
- Optional: AI models for enhanced features

### Cloud Backend
- Python 3.10+
- Docker & Docker Compose (recommended)
- Or direct Python with FastAPI/Uvicorn

## AI Models Setup (Optional)

For full AI functionality, download models to:
- `py-sales-tracker/models/llm/model.gguf` - Local LLM (4-8GB)
- Embeddings auto-download on first use (~90MB)

See `py-sales-tracker/models/llm/README.md` for download instructions.

## Environment Configuration

1. Copy `cloud-backend/.env.example` to `cloud-backend/.env`
2. Update with production values:
   ```env
   SECRET_KEY=your-super-secret-key
   SYNC_AES_KEY_BASE64=your-base64-32-bytes-key
   ADMIN_USER=admin
   ADMIN_PASS=your-secure-password
   ```

## Testing the Build

### Desktop App
```bash
# Windows
build-output\SalesTracker\SalesTracker.exe

# Linux/macOS
./build-output/SalesTracker/SalesTracker
```

### Backend API
```bash
cd build-output/cloud-backend
docker-compose up -d

# Test endpoints
curl http://localhost:8000/healthz
# Visit http://localhost:8000/admin
```

## Distribution

The `build-output/` folder contains everything needed for deployment:
1. Zip/tar the entire folder
2. Distribute to target systems
3. Follow DEPLOYMENT.md for setup instructions

## Troubleshooting

### Build Issues
- Ensure Python 3.10+ is installed
- Check all dependencies are available
- Verify sufficient disk space (2-5GB for full build)

### Runtime Issues
- Desktop: Check graphics drivers for Qt/PySide6
- Backend: Verify Docker is running
- Sync: Ensure network connectivity between components

## Support

For detailed deployment instructions, see `DEPLOYMENT.md`.
For technical issues, check application logs and error messages.
