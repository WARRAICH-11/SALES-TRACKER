# Sales Tracker (Offline-First Desktop App)

A cross-platform, offline-first desktop application for tracking sales, customers, and inventory.

## Features
- Sales entry (product, quantity, price)
- Customer management (add/edit offline)
- Inventory tracking (stock updates)
- Dashboard (daily summary, 7-day trend)
- Dark/Light mode toggle
- Keyboard shortcuts for quick sales entry (F2, Ctrl+S, Delete)
- Export reports (Excel/PDF)
- Local SQLite storage (SQLAlchemy)
- Offline queue for sync (stubbed)
- AI Insights: Local LLM Q&A, FAISS RAG over SQLite, ARIMA forecast, Plotly charts

## Stack
- Python 3.10+
- PySide6 (Qt for Python)
- SQLAlchemy + SQLite
- OpenPyXL (Excel), ReportLab (PDF)
- llama-cpp-python (local LLM), sentence-transformers + faiss-cpu (RAG), statsmodels/pandas (forecast), plotly (charts)

## Setup
1. Create virtual environment and install dependencies:
   ```bash
   python -m venv .venv
   .venv\\Scripts\\activate  # Windows
   # source .venv/bin/activate  # macOS/Linux
   pip install -r requirements.txt
   ```

2. Place offline models locally:
   - LLM (GGUF 4-bit): put at `py-sales-tracker/models/llm/model.gguf` (Llama 3 or Mistral 7B Q4)
   - Embeddings: download Sentence Transformers `all-MiniLM-L6-v2` and place at `py-sales-tracker/models/embeddings/all-MiniLM-L6-v2/`

3. Run the app:
   ```bash
   python -m app.main
   # or
   python app/main.py
   ```

4. Optional: Build executable
   ```bash
   pip install pyinstaller
   pyinstaller --noconfirm --noconsole --name SalesTracker app/main.py
   ```

## AI Notes
- Q&A uses FAISS vector search over normalized rows from `products`, `customers`, `sales`, `sale_items`; the context feeds a local LLM.
- Forecasting: 30-day horizon via ARIMA; ONNX inference is supported if `data/forecast.onnx` exists.
- Caching: frequent Q&A is cached in `data/ai_cache.json` (60 minutes).
- Plotly charts render in the AI Insights tab.

## Keyboard Shortcuts
- F2: Focus product search in Sales tab
- Ctrl+S / Cmd+S: Save current sale
- Delete: Remove selected sale line item

## Data Location
- SQLite DB file: `py-sales-tracker/data/sales.db`
- Offline queue: `py-sales-tracker/data/offline_queue.json`
- FAISS index: `py-sales-tracker/data/index/`
- Exports: `py-sales-tracker/exports/`

## Sync
A simple offline queue is implemented (append-only). Hook your API in `app/services/sync.py` to enable two-way sync when online. 

## New Features
- Upstream sync for products/customers (soft delete with `deleted_at`) using conflict resolution by `updated_at` and `external_id`.
- Profit tracking with `cost_price` on products; dashboard shows revenue and profit; AI supports margin questions.
- Background auto-sync every N minutes (default 15) via `data/settings.json`.
- AI Index Management: "Rebuild AI Index" button with progress.
- Seed data: run `python -m app.main --seed` to populate demo data and build FAISS.
- Packaging: PyInstaller spec `pyinstaller.spec` for desktop.

## Settings
`data/settings.json`:
```json
{
  "auto_sync_minutes": 15
}
```

## Backend Deployment
- Dockerfile and docker-compose.yml added in `cloud-backend/`.
- `.env.example` shows required env vars.
- Admin dashboard extended with top products and ready for profit charts. 