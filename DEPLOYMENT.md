# Sales Tracker - Deployment Guide

This guide covers deployment options for both the desktop application and cloud backend.

## Desktop Application Deployment

### Option 1: PyInstaller Executable (Recommended)

1. **Install PyInstaller**:
   ```bash
   cd py-sales-tracker
   pip install pyinstaller
   ```

2. **Build executable**:
   ```bash
   # Windows
   build_win.bat
   
   # macOS
   ./build_mac.sh
   
   # Linux
   ./build_linux.sh
   ```

3. **Distribute**: The executable will be in `dist/SalesTracker/`

### Option 2: Python Environment

1. **Setup environment**:
   ```bash
   cd py-sales-tracker
   python -m venv .venv
   .venv\Scripts\activate  # Windows
   # source .venv/bin/activate  # macOS/Linux
   pip install -r requirements.txt
   ```

2. **Download AI Models** (Optional but recommended):
   - LLM: Download a GGUF 4-bit model (Llama 3 or Mistral 7B Q4) to `models/llm/model.gguf`
   - Embeddings: `sentence-transformers` will auto-download `all-MiniLM-L6-v2` on first use

3. **Run**:
   ```bash
   python -m app.main
   ```

## Cloud Backend Deployment

### Option 1: Docker (Recommended)

1. **Build and run**:
   ```bash
   cd cloud-backend
   docker-compose up --build
   ```

2. **Environment variables** (create `.env`):
   ```env
   SECRET_KEY=your-super-secret-key-here
   SYNC_AES_KEY_BASE64=your-base64-32-bytes-key
   ADMIN_USER=admin
   ADMIN_PASS=your-admin-password
   ```

### Option 2: Direct Python

1. **Setup**:
   ```bash
   cd cloud-backend
   python -m venv .venv
   .venv\Scripts\activate  # Windows
   pip install -r requirements.txt
   ```

2. **Run**:
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```

### Option 3: Fly.io with LiteFS

1. **Install Fly CLI** and login
2. **Deploy**:
   ```bash
   cd cloud-backend
   fly deploy
   ```

## Production Considerations

### Security
- Change default admin credentials
- Use strong SECRET_KEY and AES keys
- Enable HTTPS in production
- Consider rate limiting adjustments

### Performance
- Use PostgreSQL for high-volume deployments
- Configure proper backup strategies
- Monitor resource usage

### Monitoring
- Check application logs regularly
- Monitor sync success rates
- Track API response times

## Troubleshooting

### Desktop App Issues
- **Missing AI models**: Download models to correct paths or disable AI features
- **Qt/PySide6 issues**: Ensure proper graphics drivers
- **Sync failures**: Check network connectivity and backend availability

### Backend Issues
- **Database locks**: Ensure proper connection pooling
- **Memory usage**: Monitor for memory leaks in long-running deployments
- **Sync conflicts**: Review conflict resolution logs

## Support

For issues or questions:
1. Check application logs
2. Verify environment setup
3. Test with minimal configuration
4. Review error messages for specific guidance