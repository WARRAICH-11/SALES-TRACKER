from __future__ import annotations

import sys
import json
from datetime import date
from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QApplication, QMainWindow, QTabWidget, QFileDialog, QMessageBox

from sqlalchemy.orm import Session

from app.theme import apply_dark_palette, apply_light_palette
from app.data.db import engine, get_session, DATA_DIR
from app.data.models import init_db
from app.widgets.dashboard import DashboardWidget
from app.widgets.sales_entry import SalesEntryWidget
from app.widgets.customers import CustomersWidget
from app.widgets.inventory import InventoryWidget
from app.widgets.ai_insights import AIInsightsWidget
from app.reports.export import export_sales_to_excel, export_daily_summary_pdf
from app.services.migrate import migrate
from app.services.sync import attempt_sync_with_backoff
from app.services.sync_pull import pull_updates

SETTINGS_PATH = DATA_DIR / "settings.json"


def load_settings() -> dict:
    if SETTINGS_PATH.exists():
        try:
            return json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"auto_sync_minutes": 15}


def save_settings(cfg: dict) -> None:
    SETTINGS_PATH.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")


class MainWindow(QMainWindow):
    def __init__(self, session: Session) -> None:
        super().__init__()
        self.session = session
        self.setWindowTitle("Sales Tracker")
        self.resize(1100, 720)

        self.tabs = QTabWidget()
        self.dashboard = DashboardWidget(session)
        self.sales = SalesEntryWidget(session)
        self.customers = CustomersWidget(session)
        self.inventory = InventoryWidget(session)
        self.ai_insights = AIInsightsWidget(session)

        self.tabs.addTab(self.dashboard, "Dashboard")
        self.tabs.addTab(self.sales, "Sales")
        self.tabs.addTab(self.customers, "Customers")
        self.tabs.addTab(self.inventory, "Inventory")
        self.tabs.addTab(self.ai_insights, "AI Insights")
        self.setCentralWidget(self.tabs)

        self._build_menu()
        self._init_auto_sync()

    def _build_menu(self) -> None:
        menubar = self.menuBar()

        file_menu = menubar.addMenu("File")
        export_excel_action = QAction("Export Sales to Excel", self)
        export_excel_action.triggered.connect(self._export_excel)
        file_menu.addAction(export_excel_action)

        export_pdf_action = QAction("Export Daily PDF", self)
        export_pdf_action.triggered.connect(self._export_daily_pdf)
        file_menu.addAction(export_pdf_action)

        file_menu.addSeparator()
        sync_action = QAction("Sync Now", self)
        sync_action.triggered.connect(self._sync_now)
        file_menu.addAction(sync_action)

        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        view_menu = menubar.addMenu("View")
        self.dark_mode_action = QAction("Dark Mode", self, checkable=True)
        self.dark_mode_action.triggered.connect(self._toggle_theme)
        view_menu.addAction(self.dark_mode_action)

        tools_menu = menubar.addMenu("Tools")
        refresh_action = QAction("Refresh Dashboard", self)
        refresh_action.triggered.connect(self.dashboard.refresh)
        tools_menu.addAction(refresh_action)

    def _init_auto_sync(self) -> None:
        cfg = load_settings()
        self.timer = QTimer(self)
        self.timer.setInterval(int(cfg.get("auto_sync_minutes", 15)) * 60 * 1000)
        self.timer.timeout.connect(self._background_sync)
        self.timer.start()

    def _background_sync(self) -> None:
        uploaded = attempt_sync_with_backoff(self.session)
        pulled = pull_updates(self.session)
        if uploaded or pulled:
            self.inventory.refresh()
            self.customers.refresh()
            self.dashboard.refresh()
            self.statusBar().showMessage("Auto-sync complete", 5000)
        else:
            self.statusBar().showMessage("Auto-sync skipped or failed", 5000)

    def _toggle_theme(self) -> None:
        app = QApplication.instance()
        if not app:
            return
        if self.dark_mode_action.isChecked():
            apply_dark_palette(app)
        else:
            apply_light_palette(app)

    def _export_excel(self) -> None:
        today = date.today()
        start = date.fromordinal(today.toordinal() - 30)
        end = date.fromordinal(today.toordinal() + 1)
        out_path = export_sales_to_excel(self.session, start, end)
        QMessageBox.information(self, "Export", f"Saved: {out_path}")

    def _export_daily_pdf(self) -> None:
        today = date.today()
        out_path = export_daily_summary_pdf(self.session, today)
        QMessageBox.information(self, "Export", f"Saved: {out_path}")

    def _sync_now(self) -> None:
        uploaded = attempt_sync_with_backoff(self.session)
        pulled = pull_updates(self.session)
        self.inventory.refresh()
        self.customers.refresh()
        self.dashboard.refresh()
        msg = f"Uploaded: {'yes' if uploaded else 'no'}, Pulled: {'yes' if pulled else 'no'}"
        QMessageBox.information(self, "Sync", msg)


def _bootstrap() -> None:
    init_db(engine)
    migrate(engine)


def main() -> None:
    # Seed option
    if "--seed" in sys.argv:
        from app.services.seed import seed_all
        seed_all()

    _bootstrap()
    app = QApplication(sys.argv)
    app.setApplicationName("Sales Tracker")

    apply_light_palette(app)

    with get_session() as session:
        win = MainWindow(session)
        win.show()
        sys.exit(app.exec())


if __name__ == "__main__":
    main() 