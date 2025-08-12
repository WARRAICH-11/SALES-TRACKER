from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal
import random

from app.data.db import get_session
from app.data.models import Product, Customer, Sale, SaleItem
from app.ai.rag import SalesRAG


def seed_all() -> None:
    with get_session() as session:
        # Products
        names = [
            ("Widget A", 9.99, 5.50), ("Widget B", 19.99, 11.00), ("Gadget C", 29.99, 18.00),
            ("Thing D", 4.99, 2.00), ("Thing E", 14.99, 8.00)
        ]
        for n, price, cost in names:
            p = Product(name=n, price=Decimal(price), cost_price=Decimal(cost), stock=100, updated_at=datetime.utcnow())
            session.add(p)
        # Customers
        for i in range(1, 11):
            c = Customer(name=f"Customer {i}", email=f"c{i}@email.com", phone="", updated_at=datetime.utcnow())
            session.add(c)
        session.commit()

        products = session.query(Product).all()
        customers = session.query(Customer).all()

        now = datetime.utcnow()
        # Sales last 30 days
        for d in range(30):
            day = now - timedelta(days=d)
            for _ in range(random.randint(3, 10)):
                sale = Sale(customer_id=random.choice(customers).id if customers else None, created_at=day)
                session.add(sale)
                session.flush()
                for _ in range(random.randint(1, 3)):
                    prod = random.choice(products)
                    qty = random.randint(1, 5)
                    session.add(SaleItem(sale_id=sale.id, product_id=prod.id, quantity=qty, price=prod.price))
        session.commit()

        # Build AI index
        rag = SalesRAG(session)
        rag.rebuild_index() 