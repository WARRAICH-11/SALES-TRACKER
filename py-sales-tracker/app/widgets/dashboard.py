from __future__ import annotations

from datetime import datetime, timedelta, date
from decimal import Decimal
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QTableWidget, QTableWidgetItem
from sqlalchemy.orm import Session
from sqlalchemy import select, func

from app.data.models import Sale, SaleItem, Product


class DashboardWidget(QWidget):
    def __init__(self, session: Session, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.session = session

        self.total_label = QLabel("")
        self.profit_label = QLabel("")
        self.trend_table = QTableWidget(0, 3)
        self.trend_table.setHorizontalHeaderLabels(["Day", "Revenue", "Profit"])
        self.trend_table.horizontalHeader().setStretchLastSection(True)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Daily Sales Summary"))
        layout.addWidget(self.total_label)
        layout.addWidget(self.profit_label)
        layout.addWidget(QLabel("7-Day Trend"))
        layout.addWidget(self.trend_table)

        self.refresh()

    def refresh(self) -> None:
        today = date.today()
        tomorrow = date.fromordinal(today.toordinal() + 1)

        rev_stmt = (
            select(func.sum(SaleItem.quantity * SaleItem.price))
            .join(SaleItem, Sale.id == SaleItem.sale_id)
            .where(Sale.created_at >= today, Sale.created_at < tomorrow)
        )
        revenue = Decimal(self.session.execute(rev_stmt).scalar() or 0)

        profit_stmt = (
            select(func.sum(SaleItem.quantity * (SaleItem.price - Product.cost_price)))
            .join(SaleItem, Sale.id == SaleItem.sale_id)
            .join(Product, Product.id == SaleItem.product_id)
            .where(Sale.created_at >= today, Sale.created_at < tomorrow)
        )
        profit = Decimal(self.session.execute(profit_stmt).scalar() or 0)

        self.total_label.setText(f"Today Revenue: {float(revenue):.2f}")
        self.profit_label.setText(f"Today Profit: {float(profit):.2f}")

        # 7-day trend
        self.trend_table.setRowCount(0)
        for i in range(6, -1, -1):
            day = date.fromordinal(today.toordinal() - i)
            nxt = date.fromordinal(day.toordinal() + 1)
            day_rev_stmt = (
                select(func.sum(SaleItem.quantity * SaleItem.price))
                .join(SaleItem, Sale.id == SaleItem.sale_id)
                .where(Sale.created_at >= day, Sale.created_at < nxt)
            )
            day_profit_stmt = (
                select(func.sum(SaleItem.quantity * (SaleItem.price - Product.cost_price)))
                .join(SaleItem, Sale.id == SaleItem.sale_id)
                .join(Product, Product.id == SaleItem.product_id)
                .where(Sale.created_at >= day, Sale.created_at < nxt)
            )
            day_rev = self.session.execute(day_rev_stmt).scalar() or 0
            day_profit = self.session.execute(day_profit_stmt).scalar() or 0
            row = self.trend_table.rowCount()
            self.trend_table.insertRow(row)
            self.trend_table.setItem(row, 0, QTableWidgetItem(day.isoformat()))
            self.trend_table.setItem(row, 1, QTableWidgetItem(f"{float(day_rev):.2f}"))
            self.trend_table.setItem(row, 2, QTableWidgetItem(f"{float(day_profit):.2f}")) 