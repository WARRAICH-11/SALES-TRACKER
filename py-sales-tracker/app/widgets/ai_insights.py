from __future__ import annotations

from datetime import date, datetime, timedelta
from pathlib import Path
import json
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTextEdit, QLineEdit, QLabel, QMessageBox, QProgressBar, QGroupBox
)
from sqlalchemy.orm import Session
from sqlalchemy import select, func

from app.ai.rag import SalesRAG
from app.ai.forecast import train_arima_and_forecast
from app.ai.cache import set_cached_answer
from app.ai.config import FAISS_INDEX_PATH, DOCSTORE_PATH, CACHE_PATH

try:
    import plotly.graph_objs as go
    from plotly.offline import plot
except Exception:  # pragma: no cover
    go = None  # type: ignore
    plot = None  # type: ignore

try:
    from PySide6.QtWebEngineWidgets import QWebEngineView  # type: ignore
except Exception:  # pragma: no cover
    QWebEngineView = None  # type: ignore

from app.data.models import Sale, SaleItem, Product

DATA_DIR = Path(__file__).resolve().parents[2] / 'data'
INSIGHTS_PATH = DATA_DIR / 'quick_insights.json'


class IndexWorker(QThread):
    progressed = Signal(int)
    finished_ok = Signal()
    failed = Signal(str)

    def __init__(self, session: Session) -> None:
        super().__init__()
        self.session = session

    def run(self) -> None:  # type: ignore[override]
        try:
            # Clear existing
            for p in [FAISS_INDEX_PATH, DOCSTORE_PATH, CACHE_PATH]:
                try:
                    Path(p).unlink(missing_ok=True)
                except Exception:
                    pass
            rag = SalesRAG(self.session)
            rag.doc_texts = []
            rag.rebuild_index()
            self.progressed.emit(100)
            self.finished_ok.emit()
        except Exception as e:
            self.failed.emit(str(e))


class InsightsWorker(QThread):
    done = Signal(dict)
    failed = Signal(str)

    def __init__(self, session: Session) -> None:
        super().__init__()
        self.session = session

    def run(self) -> None:  # type: ignore[override]
        try:
            today = date.today()
            yesterday = date.fromordinal(today.toordinal() - 1)
            # Yesterday revenue & profit
            start = yesterday
            end = date.fromordinal(yesterday.toordinal() + 1)
            rev = self._sum_revenue(start, end)
            prof = self._sum_profit(start, end)

            # Top-selling product last 7 days by revenue
            week_start = date.fromordinal(today.toordinal() - 7)
            top_stmt = (
                select(Product.name, func.sum(SaleItem.quantity * SaleItem.price))
                .join(SaleItem, Product.id == SaleItem.product_id)
                .join(Sale, Sale.id == SaleItem.sale_id)
                .where(Sale.created_at >= week_start, Sale.created_at < today)
                .group_by(Product.name)
                .order_by(func.sum(SaleItem.quantity * SaleItem.price).desc())
                .limit(1)
            )
            top = self.session.execute(top_stmt).first()
            top_name = top[0] if top else 'N/A'

            # Category with largest WoW drop (last 7 vs prior 7)
            prev_start = date.fromordinal(today.toordinal() - 14)
            prev_mid = date.fromordinal(today.toordinal() - 7)
            cat_stmt = (
                select(Product.category, func.sum(SaleItem.quantity * SaleItem.price))
                .join(SaleItem, Product.id == SaleItem.product_id)
                .join(Sale, Sale.id == SaleItem.sale_id)
                .where(Sale.created_at >= prev_start, Sale.created_at < prev_mid)
                .group_by(Product.category)
            )
            prev_map = {c or 'Uncategorized': float(v or 0) for c, v in self.session.execute(cat_stmt)}
            last_stmt = (
                select(Product.category, func.sum(SaleItem.quantity * SaleItem.price))
                .join(SaleItem, Product.id == SaleItem.product_id)
                .join(Sale, Sale.id == SaleItem.sale_id)
                .where(Sale.created_at >= prev_mid, Sale.created_at < today)
                .group_by(Product.category)
            )
            last_map = {c or 'Uncategorized': float(v or 0) for c, v in self.session.execute(last_stmt)}
            all_cats = set(prev_map) | set(last_map)
            worst_cat = 'N/A'
            worst_drop = 0.0
            for c in all_cats:
                p = prev_map.get(c, 0.0)
                l = last_map.get(c, 0.0)
                drop = (l - p) / p * 100.0 if p > 0 else (0.0 if l == 0 else -100.0)
                if drop < worst_drop:
                    worst_drop = drop
                    worst_cat = c

            result = {
                'ts': datetime.utcnow().isoformat(),
                'yesterday_revenue': round(rev, 2),
                'yesterday_profit': round(prof, 2),
                'top_product_last_7_days': top_name,
                'worst_category_wow_drop': worst_cat,
                'worst_category_drop_pct': round(worst_drop, 1),
            }
            self.done.emit(result)
        except Exception as e:
            self.failed.emit(str(e))

    def _sum_revenue(self, start, end) -> float:
        stmt = (
            select(func.sum(SaleItem.quantity * SaleItem.price))
            .join(SaleItem, Sale.id == SaleItem.sale_id)
            .where(Sale.created_at >= start, Sale.created_at < end)
        )
        return float(self.session.execute(stmt).scalar() or 0.0)

    def _sum_profit(self, start, end) -> float:
        stmt = (
            select(func.sum(SaleItem.quantity * (SaleItem.price - Product.cost_price)))
            .join(SaleItem, Sale.id == SaleItem.sale_id)
            .join(Product, Product.id == SaleItem.product_id)
            .where(Sale.created_at >= start, Sale.created_at < end)
        )
        return float(self.session.execute(stmt).scalar() or 0.0)


class AIInsightsWidget(QWidget):
    def __init__(self, session: Session, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.session = session

        # Q&A
        self.query_input = QLineEdit()
        self.query_input.setPlaceholderText("Ask: e.g., Top-selling products this month, profit/margin last week, etc.")
        self.ask_btn = QPushButton("Ask AI")
        self.answer_view = QTextEdit()
        self.answer_view.setReadOnly(True)

        # Forecast / Chart / Index
        self.forecast_btn = QPushButton("Run 30-day Forecast")
        self.insights_btn = QPushButton("Generate Insights")
        self.rebuild_btn = QPushButton("Rebuild AI Index")
        self.progress = QProgressBar()
        self.progress.setValue(0)
        if QWebEngineView is not None:
            self.chart_view = QWebEngineView()
        else:
            self.chart_view = QLabel("Install PySide6 with QtWebEngine to render charts.")  # type: ignore

        # Quick Insights panel
        self.insights_group = QGroupBox("Quick Insights (24h cache)")
        self.insights_text = QTextEdit()
        self.insights_text.setReadOnly(True)
        self.refresh_insights_btn = QPushButton("Refresh Insights")
        il = QVBoxLayout()
        il.addWidget(self.insights_text)
        il.addWidget(self.refresh_insights_btn)
        self.insights_group.setLayout(il)

        # Layout
        qa = QHBoxLayout()
        qa.addWidget(self.query_input)
        qa.addWidget(self.ask_btn)

        actions = QHBoxLayout()
        actions.addWidget(self.forecast_btn)
        actions.addWidget(self.insights_btn)
        actions.addWidget(self.rebuild_btn)
        actions.addWidget(self.progress)
        actions.addStretch(1)

        layout = QVBoxLayout(self)
        layout.addLayout(qa)
        layout.addWidget(self.insights_group)
        layout.addWidget(self.answer_view)
        layout.addLayout(actions)
        layout.addWidget(self.chart_view)

        self.ask_btn.clicked.connect(self._ask)
        self.forecast_btn.clicked.connect(self._forecast)
        self.insights_btn.clicked.connect(self._insights)
        self.rebuild_btn.clicked.connect(self._rebuild)
        self.refresh_insights_btn.clicked.connect(self._refresh_insights)

        self._load_cached_insights()

    def _ask(self) -> None:
        q = self.query_input.text().strip()
        if not q:
            return
        try:
            rag = SalesRAG(self.session)
            ans = rag.answer(q + "\nIf about margins, profit = sum(quantity*(price-cost_price)).")
            self.answer_view.setText(ans)
        except Exception as e:
            QMessageBox.warning(self, "AI Error", str(e))

    def _forecast(self) -> None:
        try:
            result = train_arima_and_forecast(self.session)
            if go is None or plot is None:
                self._set_chart_html("Plotly not installed. Install plotly to see the chart.")
                return
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=result.dates, y=result.values, mode="lines+markers", name="Forecast"))
            fig.update_layout(title="30-Day Revenue Forecast", xaxis_title="Date", yaxis_title="Revenue")
            html = plot(fig, output_type="div", include_plotlyjs=True)
            self._set_chart_html(html)
        except Exception as e:
            QMessageBox.warning(self, "Forecast Error", str(e))

    def _insights(self) -> None:
        try:
            today = date.today()
            start_prev = today - timedelta(days=14)
            mid = today - timedelta(days=7)

            prev_total = self._sum_revenue(start_prev, mid)
            last_total = self._sum_revenue(mid, today + timedelta(days=1))
            change = 0.0 if prev_total == 0 else ((last_total - prev_total) / prev_total) * 100.0
            direction = "increased" if change >= 0 else "dropped"

            self.answer_view.append(f"\nSales {direction} {abs(change):.1f}% this week (last 7 days: {last_total:.2f}, prior 7 days: {prev_total:.2f}).")
        except Exception as e:
            QMessageBox.warning(self, "Insights Error", str(e))

    def _rebuild(self) -> None:
        self.progress.setValue(5)
        self.worker = IndexWorker(self.session)
        self.worker.progressed.connect(self.progress.setValue)
        self.worker.finished_ok.connect(lambda: QMessageBox.information(self, "Index", "Rebuilt successfully."))
        self.worker.failed.connect(lambda m: QMessageBox.warning(self, "Index", m))
        self.worker.start()

    def _load_cached_insights(self) -> None:
        try:
            if INSIGHTS_PATH.exists():
                data = json.loads(INSIGHTS_PATH.read_text(encoding='utf-8'))
                ts = datetime.fromisoformat(data.get('ts', '1970-01-01T00:00:00'))
                if datetime.utcnow() - ts < timedelta(hours=24):
                    self._render_insights(data)
                    return
        except Exception:
            pass
        self._refresh_insights()

    def _refresh_insights(self) -> None:
        self.insights_text.setText("Refreshing insights...")
        self.worker2 = InsightsWorker(self.session)
        self.worker2.done.connect(self._insights_ready)
        self.worker2.failed.connect(lambda m: self.insights_text.setText(f"Failed: {m}"))
        self.worker2.start()

    def _insights_ready(self, data: dict) -> None:
        try:
            INSIGHTS_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
        except Exception:
            pass
        self._render_insights(data)

    def _render_insights(self, data: dict) -> None:
        lines = [
            f"Yesterday Revenue: {data.get('yesterday_revenue', 0):.2f}",
            f"Yesterday Profit: {data.get('yesterday_profit', 0):.2f}",
            f"Top Product (7d): {data.get('top_product_last_7_days', 'N/A')}",
            f"Worst Category WoW Drop: {data.get('worst_category_wow_drop', 'N/A')} ({data.get('worst_category_drop_pct', 0)}%)",
        ]
        self.insights_text.setText("\n".join(lines))

    def _sum_revenue(self, start, end) -> float:
        stmt = (
            select(func.sum(SaleItem.quantity * SaleItem.price))
            .join(SaleItem, Sale.id == SaleItem.sale_id)
            .where(Sale.created_at >= start, Sale.created_at < end)
        )
        return float(self.session.execute(stmt).scalar() or 0.0)

    def _set_chart_html(self, html: str) -> None:
        if QWebEngineView is not None and hasattr(self, "chart_view") and hasattr(self.chart_view, "setHtml"):
            self.chart_view.setHtml(html)  # type: ignore
        elif isinstance(self.chart_view, QLabel):
            self.chart_view.setText("Chart cannot be rendered without QtWebEngine.") 