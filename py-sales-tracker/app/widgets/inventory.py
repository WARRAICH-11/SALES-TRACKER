from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget, QTableWidgetItem,
    QLineEdit, QMessageBox
)
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.data.models import Product, Sale, SaleItem
from app.services.sync import enqueue


class InventoryWidget(QWidget):
    def __init__(self, session: Session, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.session = session

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search products...")
        self.add_btn = QPushButton("Add")
        self.edit_btn = QPushButton("Edit")
        self.delete_btn = QPushButton("Archive")

        top = QHBoxLayout()
        top.addWidget(self.search_input)
        top.addWidget(self.add_btn)
        top.addWidget(self.edit_btn)
        top.addWidget(self.delete_btn)

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["ID", "Name", "Category", "Price", "Cost", "Stock"])
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.horizontalHeader().setStretchLastSection(True)

        layout = QVBoxLayout(self)
        layout.addLayout(top)
        layout.addWidget(self.table)

        self.add_btn.clicked.connect(self.add_product)
        self.edit_btn.clicked.connect(self.edit_product)
        self.delete_btn.clicked.connect(self.archive_product)
        self.search_input.textChanged.connect(self.refresh)

        self.refresh()

    def refresh(self) -> None:
        text = self.search_input.text().strip()
        stmt = select(Product).where(Product.deleted_at.is_(None))
        if text:
            stmt = stmt.where(Product.name.ilike(f"%{text}%"))
        products = self.session.execute(stmt).scalars().all()

        self.table.setRowCount(0)
        for p in products:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(str(p.id)))
            self.table.setItem(row, 1, QTableWidgetItem(p.name))
            self.table.setItem(row, 2, QTableWidgetItem(p.category or "Uncategorized"))
            self.table.setItem(row, 3, QTableWidgetItem(f"{float(p.price):.2f}"))
            self.table.setItem(row, 4, QTableWidgetItem(f"{float(p.cost_price or 0):.2f}"))
            self.table.setItem(row, 5, QTableWidgetItem(str(p.stock)))

    def _selected_product(self) -> Product | None:
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            return None
        pid = int(self.table.item(rows[0].row(), 0).text())
        return self.session.get(Product, pid)

    def add_product(self) -> None:
        name, category, price, cost, stock = self._prompt_product()
        if not name:
            return
        self.session.add(Product(
            name=name,
            category=category or None,
            price=Decimal(price or "0"),
            cost_price=Decimal(cost or "0"),
            stock=int(stock or 0),
            updated_at=datetime.utcnow(),
        ))
        self.session.commit()
        self.refresh()

    def edit_product(self) -> None:
        prod = self._selected_product()
        if not prod:
            QMessageBox.information(self, "Edit Product", "Select a product first.")
            return
        name, category, price, cost, stock = self._prompt_product(prod.name, prod.category or "", f"{float(prod.price):.2f}", f"{float(prod.cost_price or 0):.2f}", str(prod.stock))
        if not name:
            return
        prod.name = name
        prod.category = category or None
        prod.price = Decimal(price or "0")
        prod.cost_price = Decimal(cost or "0")
        prod.stock = int(stock or 0)
        prod.updated_at = datetime.utcnow()
        self.session.commit()
        self.refresh()

    def archive_product(self) -> None:
        prod = self._selected_product()
        if not prod:
            return
        # guard: recent sales
        cutoff = datetime.utcnow() - timedelta(days=30)
        recent = self.session.execute(
            select(func.count(SaleItem.id)).join(Sale, Sale.id == SaleItem.sale_id).where(SaleItem.product_id == prod.id, Sale.created_at >= cutoff)
        ).scalar()
        if recent and recent > 0:
            if QMessageBox.question(self, "Recent Sales", f"Product has {recent} recent sales. Archive anyway?") != QMessageBox.Yes:
                return
        if QMessageBox.question(self, "Archive", f"Archive product '{prod.name}'?") == QMessageBox.Yes:
            prod.deleted_at = datetime.utcnow()
            prod.updated_at = datetime.utcnow()
            self.session.commit()
            enqueue("product_archived", {"product_id": prod.id})
            self.refresh()

    def _prompt_product(self, name: str = "", category: str = "", price: str = "0.00", cost: str = "0.00", stock: str = "0") -> tuple[str, str, str, str, str]:
        from PySide6.QtWidgets import QDialog, QFormLayout, QDialogButtonBox
        dlg = QDialog(self)
        dlg.setWindowTitle("Product")
        name_edit = QLineEdit(name)
        category_edit = QLineEdit(category)
        price_edit = QLineEdit(price)
        cost_edit = QLineEdit(cost)
        stock_edit = QLineEdit(stock)
        form = QFormLayout(dlg)
        form.addRow("Name", name_edit)
        form.addRow("Category", category_edit)
        form.addRow("Price", price_edit)
        form.addRow("Cost", cost_edit)
        form.addRow("Stock", stock_edit)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dlg.accept)
        buttons.rejected.connect(dlg.reject)
        form.addWidget(buttons)
        if dlg.exec() == QDialog.Accepted:
            return name_edit.text().strip(), category_edit.text().strip(), price_edit.text().strip(), cost_edit.text().strip(), stock_edit.text().strip()
        return "", "", "", "", "" 