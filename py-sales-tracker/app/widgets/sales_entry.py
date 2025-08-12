from __future__ import annotations

from decimal import Decimal
from datetime import datetime
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QKeySequence, QAction
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QSpinBox, QPushButton,
    QTableWidget, QTableWidgetItem, QMessageBox, QLineEdit
)
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.data.models import Product, Customer, Sale, SaleItem
from app.services.sync import enqueue


class SalesEntryWidget(QWidget):
    def __init__(self, session: Session, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.session = session

        # Customer selection
        self.customer_combo = QComboBox()
        self._reload_customers()

        # Product search and controls
        self.product_search = QLineEdit()
        self.product_search.setPlaceholderText("Search product (F2 to focus)...")
        self.product_combo = QComboBox()
        self._reload_products()
        self.qty_spin = QSpinBox()
        self.qty_spin.setRange(1, 10_000)
        self.add_btn = QPushButton("Add Item")

        # Items table
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Product", "Qty", "Price", "Total"]) 
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.horizontalHeader().setStretchLastSection(True)

        # Total label and actions
        self.total_label = QLabel("Total: 0.00")
        self.save_btn = QPushButton("Save Sale (Ctrl+S)")
        self.remove_btn = QPushButton("Remove Line (Del)")

        # Layouts
        top = QHBoxLayout()
        top.addWidget(QLabel("Customer"))
        top.addWidget(self.customer_combo)
        top.addSpacing(16)
        top.addWidget(self.product_search, 3)
        top.addWidget(self.product_combo, 2)
        top.addWidget(QLabel("Qty"))
        top.addWidget(self.qty_spin)
        top.addWidget(self.add_btn)

        bottom = QHBoxLayout()
        bottom.addWidget(self.total_label)
        bottom.addStretch(1)
        bottom.addWidget(self.remove_btn)
        bottom.addWidget(self.save_btn)

        layout = QVBoxLayout(self)
        layout.addLayout(top)
        layout.addWidget(self.table)
        layout.addLayout(bottom)

        # Signals
        self.add_btn.clicked.connect(self.add_item)
        self.save_btn.clicked.connect(self.save_sale)
        self.remove_btn.clicked.connect(self.remove_selected)
        self.product_search.textChanged.connect(self._filter_products)

        # Shortcuts
        focus_action = QAction(self)
        focus_action.setShortcut(QKeySequence(Qt.Key_F2))
        focus_action.triggered.connect(lambda: self.product_search.setFocus())
        self.addAction(focus_action)

        save_action = QAction(self)
        save_action.setShortcut(QKeySequence.Save)
        save_action.triggered.connect(self.save_sale)
        self.addAction(save_action)

        del_action = QAction(self)
        del_action.setShortcut(QKeySequence.Delete)
        del_action.triggered.connect(self.remove_selected)
        self.addAction(del_action)

    def _reload_customers(self) -> None:
        self.customer_combo.clear()
        customers = self.session.execute(select(Customer)).scalars().all()
        self.customer_combo.addItem("Walk-in", None)  # None means no specific customer
        for c in customers:
            self.customer_combo.addItem(c.name, c.id)

    def _reload_products(self) -> None:
        self.product_combo.clear()
        products = self.session.execute(select(Product).order_by(Product.name)).scalars().all()
        for p in products:
            self.product_combo.addItem(f"{p.name} (${float(p.price):.2f}) [Stock:{p.stock}]", p.id)

    def _filter_products(self, text: str) -> None:
        text = (text or "").strip().lower()
        self.product_combo.clear()
        stmt = select(Product)
        if text:
            stmt = stmt.where(Product.name.ilike(f"%{text}%")).order_by(Product.name)
        else:
            stmt = stmt.order_by(Product.name)
        products = self.session.execute(stmt).scalars().all()
        for p in products:
            self.product_combo.addItem(f"{p.name} (${float(p.price):.2f}) [Stock:{p.stock}]", p.id)

    def add_item(self) -> None:
        pid = self.product_combo.currentData()
        if pid is None:
            return
        product = self.session.get(Product, pid)
        if not product:
            return
        qty = int(self.qty_spin.value())
        if qty <= 0:
            return
        if product.stock < qty:
            QMessageBox.warning(self, "Insufficient Stock", f"Not enough stock for {product.name}.")
            return

        row = self.table.rowCount()
        self.table.insertRow(row)
        self.table.setItem(row, 0, QTableWidgetItem(product.name))
        self.table.setItem(row, 1, QTableWidgetItem(str(qty)))
        self.table.setItem(row, 2, QTableWidgetItem(f"{float(product.price):.2f}"))
        self.table.setItem(row, 3, QTableWidgetItem(f"{float(Decimal(qty) * Decimal(product.price)):.2f}"))
        self.update_total()

    def remove_selected(self) -> None:
        rows = sorted({i.row() for i in self.table.selectedIndexes()}, reverse=True)
        for r in rows:
            self.table.removeRow(r)
        self.update_total()

    def update_total(self) -> None:
        total = Decimal("0.00")
        for r in range(self.table.rowCount()):
            total += Decimal(self.table.item(r, 3).text())
        self.total_label.setText(f"Total: {float(total):.2f}")

    def save_sale(self) -> None:
        if self.table.rowCount() == 0:
            QMessageBox.information(self, "Save", "No items to save.")
            return

        customer_id = self.customer_combo.currentData()
        sale = Sale(customer_id=customer_id)
        self.session.add(sale)
        self.session.flush()

        # Validate stock again and deduct
        for r in range(self.table.rowCount()):
            name = self.table.item(r, 0).text()
            qty = int(self.table.item(r, 1).text())
            price = Decimal(self.table.item(r, 2).text())
            product = self.session.execute(select(Product).where(Product.name == name)).scalar_one()
            if product.stock < qty:
                self.session.rollback()
                QMessageBox.warning(self, "Insufficient Stock", f"Not enough stock for {product.name}.")
                return
            product.stock -= qty
            self.session.add(SaleItem(sale_id=sale.id, product_id=product.id, quantity=qty, price=price))

        self.session.commit()
        enqueue("sale_created", {"sale_id": sale.id})
        QMessageBox.information(self, "Saved", f"Sale #{sale.id} saved.")
        self.table.setRowCount(0)
        self.update_total()
        self._reload_products() 