from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.engine import Engine

TARGET_VERSION = 3  # bump when migrations change


def migrate(engine: Engine) -> None:
    with engine.connect() as conn:
        conn.execute(text("CREATE TABLE IF NOT EXISTS schema_version (id INTEGER PRIMARY KEY CHECK (id=1), version INTEGER NOT NULL);"))
        row = conn.execute(text("SELECT version FROM schema_version WHERE id=1;")).fetchone()
        current = row[0] if row else 0
        if current >= TARGET_VERSION:
            return
        conn.execute(text("PRAGMA foreign_keys=off;"))
        # Products
        if _can_add(conn, 'products', 'external_id'):
            conn.execute(text("ALTER TABLE products ADD COLUMN external_id VARCHAR(64);"))
        if _can_add(conn, 'products', 'updated_at'):
            conn.execute(text("ALTER TABLE products ADD COLUMN updated_at DATETIME;"))
        if _can_add(conn, 'products', 'cost_price'):
            conn.execute(text("ALTER TABLE products ADD COLUMN cost_price NUMERIC;"))
            conn.execute(text("UPDATE products SET cost_price = price * 0.6 WHERE cost_price IS NULL;"))
        if _can_add(conn, 'products', 'deleted_at'):
            conn.execute(text("ALTER TABLE products ADD COLUMN deleted_at DATETIME;"))
        if _can_add(conn, 'products', 'category'):
            conn.execute(text("ALTER TABLE products ADD COLUMN category VARCHAR(255);"))
            conn.execute(text("UPDATE products SET category = 'Uncategorized' WHERE category IS NULL;"))
        # Customers
        if _can_add(conn, 'customers', 'external_id'):
            conn.execute(text("ALTER TABLE customers ADD COLUMN external_id VARCHAR(64);"))
        if _can_add(conn, 'customers', 'updated_at'):
            conn.execute(text("ALTER TABLE customers ADD COLUMN updated_at DATETIME;"))
        if _can_add(conn, 'customers', 'deleted_at'):
            conn.execute(text("ALTER TABLE customers ADD COLUMN deleted_at DATETIME;"))
        conn.execute(text("PRAGMA foreign_keys=on;"))
        # Bump version
        if row:
            conn.execute(text("UPDATE schema_version SET version=:v WHERE id=1"), {"v": TARGET_VERSION})
        else:
            conn.execute(text("INSERT INTO schema_version(id, version) VALUES (1, :v)"), {"v": TARGET_VERSION})


def _can_add(conn, table: str, column: str) -> bool:
    res = conn.execute(text(f"PRAGMA table_info({table});")).mappings().all()
    return all(row["name"] != column for row in res) 