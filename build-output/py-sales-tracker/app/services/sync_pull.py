from __future__ import annotations

import os
from datetime import datetime
from typing import Any

import requests
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.data.models import Product, Customer
from app.services.sync import _load_state, _save_state, _get_token

SYNC_SERVER = os.getenv("SYNC_SERVER", "http://127.0.0.1:8000")


def _parse_dt(s: str) -> datetime:
    try:
        return datetime.fromisoformat(s)
    except Exception:
        return datetime.utcnow()


def pull_updates(session: Session) -> bool:
    state = _load_state()
    since = state.get("last_download", "1970-01-01T00:00:00")
    token = _get_token()
    if not token:
        return False

    try:
        r = requests.get(f"{SYNC_SERVER}/sync/download", params={"since": since}, headers={"Authorization": f"Bearer {token}"}, timeout=8)
        r.raise_for_status()
        data = r.json()
    except Exception:
        return False

    changed = False

    for p in data.get("products", []):
        existing = None
        if p.get("external_id"):
            existing = session.execute(select(Product).where(Product.external_id == p["external_id"])) .scalar_one_or_none()
        if existing:
            if not existing.updated_at or _parse_dt(p["updated_at"]) > existing.updated_at:
                existing.name = p["name"]
                existing.price = p["price"]
                existing.cost_price = p.get("cost_price") or existing.cost_price
                existing.stock = p["stock"]
                existing.updated_at = _parse_dt(p["updated_at"]) 
                existing.deleted_at = _parse_dt(p["deleted_at"]) if p.get("deleted_at") else None
                changed = True
        else:
            row = Product(
                external_id=p.get("external_id"),
                name=p["name"],
                price=p["price"],
                cost_price=p.get("cost_price"),
                stock=p["stock"],
                updated_at=_parse_dt(p["updated_at"]),
                deleted_at=_parse_dt(p["deleted_at"]) if p.get("deleted_at") else None,
            )
            session.add(row)
            changed = True

    for c in data.get("customers", []):
        existing = None
        if c.get("external_id"):
            existing = session.execute(select(Customer).where(Customer.external_id == c["external_id"])) .scalar_one_or_none()
        if existing:
            if not existing.updated_at or _parse_dt(c["updated_at"]) > existing.updated_at:
                existing.name = c["name"]
                existing.email = c.get("email")
                existing.phone = c.get("phone")
                existing.updated_at = _parse_dt(c["updated_at"]) 
                existing.deleted_at = _parse_dt(c["deleted_at"]) if c.get("deleted_at") else None
                changed = True
        else:
            row = Customer(
                external_id=c.get("external_id"),
                name=c["name"],
                email=c.get("email"),
                phone=c.get("phone"),
                updated_at=_parse_dt(c["updated_at"]),
                deleted_at=_parse_dt(c["deleted_at"]) if c.get("deleted_at") else None,
            )
            session.add(row)
            changed = True

    if changed:
        session.commit()

    # Advance watermark
    state["last_download"] = data.get("server_time")
    _save_state(state)
    return changed 