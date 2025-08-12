#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/py-sales-tracker"
python3 -m pip install --upgrade pip
pip3 install -r requirements.txt pyinstaller
pyinstaller --clean --noconfirm pyinstaller.spec
echo "Built binary in dist/SalesTracker" 