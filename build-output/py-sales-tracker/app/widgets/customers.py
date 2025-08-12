from __future__ import annotations

from datetime import datetime
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget, QTableWidgetItem,
    QLineEdit, QMessageBox
)
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.data.models import Customer
from app.services.sync import enqueue


class CustomersWidget(QWidget):
    def __init__(self, session: Session, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.session = session

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search customers...")
        self.add_btn = QPushButton("Add")
        self.edit_btn = QPushButton("Edit")
        self.delete_btn = QPushButton("Archive")

        top = QHBoxLayout()
        top.addWidget(self.search_input)
        top.addWidget(self.add_btn)
        top.addWidget(self.edit_btn)
        top.addWidget(self.delete_btn)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["ID", "Name", "Email", "Phone"])
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.horizontalHeader().setStretchLastSection(True)

        layout = QVBoxLayout(self)
        layout.addLayout(top)
        layout.addWidget(self.table)

        self.add_btn.clicked.connect(self.add_customer)
        self.edit_btn.clicked.connect(self.edit_customer)
        self.delete_btn.clicked.connect(self.archive_customer)
        self.search_input.textChanged.connect(self.refresh)

        self.refresh()

    def refresh(self) -> None:
        text = self.search_input.text().strip()
        stmt = select(Customer).where(Customer.deleted_at.is_(None))
        if text:
            stmt = stmt.where(Customer.name.ilike(f"%{text}%"))
        customers = self.session.execute(stmt).scalars().all()

        self.table.setRowCount(0)
        for c in customers:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(str(c.id)))
            self.table.setItem(row, 1, QTableWidgetItem(c.name))
            self.table.setItem(row, 2, QTableWidgetItem(c.email or ""))
            self.table.setItem(row, 3, QTableWidgetItem(c.phone or ""))

    def _selected_customer(self) -> Customer | None:
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            return None
        cid = int(self.table.item(rows[0].row(), 0).text())
        return self.session.get(Customer, cid)

    def add_customer(self) -> None:
        name, email, phone = self._prompt_customer()
        if not name:
            return
        self.session.add(Customer(name=name, email=email or None, phone=phone or None, updated_at=datetime.utcnow()))
        self.session.commit()
        self.refresh()

    def edit_customer(self) -> None:
        cust = self._selected_customer()
        if not cust:
            QMessageBox.information(self, "Edit Customer", "Select a customer first.")
            return
        name, email, phone = self._prompt_customer(cust.name, cust.email or "", cust.phone or "")
        if not name:
            return
        cust.name, cust.email, cust.phone = name, (email or None), (phone or None)
        cust.updated_at = datetime.utcnow()
        self.session.commit()
        self.refresh()

    def archive_customer(self) -> None:
        cust = self._selected_customer()
        if not cust:
            return
        if QMessageBox.question(self, "Archive", f"Archive customer '{cust.name}'?") == QMessageBox.Yes:
            cust.deleted_at = datetime.utcnow()
            cust.updated_at = datetime.utcnow()
            self.session.commit()
            enqueue("customer_archived", {"customer_id": cust.id})
            self.refresh()

    def _prompt_customer(self, name: str = "", email: str = "", phone: str = "") -> tuple[str, str, str]:
        from PySide6.QtWidgets import QDialog, QFormLayout, QDialogButtonBox
        dlg = QDialog(self)
        dlg.setWindowTitle("Customer")
        name_edit = QLineEdit(name)
        email_edit = QLineEdit(email)
        phone_edit = QLineEdit(phone)
        form = QFormLayout(dlg)
        form.addRow("Name", name_edit)
        form.addRow("Email", email_edit)
        form.addRow("Phone", phone_edit)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dlg.accept)
        buttons.rejected.connect(dlg.reject)
        form.addWidget(buttons)
        if dlg.exec() == QDialog.Accepted:
            return name_edit.text().strip(), email_edit.text().strip(), phone_edit.text().strip()
        return "", "", "" 