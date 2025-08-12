@echo off
setlocal
cd /d %~dp0\py-sales-tracker
python -m pip install --upgrade pip
pip install -r requirements.txt pyinstaller
pyinstaller --clean --noconfirm pyinstaller.spec
if %errorlevel% neq 0 exit /b %errorlevel%
echo Built to dist\SalesTracker\
endlocal 