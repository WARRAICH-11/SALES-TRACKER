from __future__ import annotations

import json
import os
import base64
import time
import gzip
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

import requests
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from sqlalchemy import select

from app.data.models import Product, Customer
import random

BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
QUEUE_PATH = DATA_DIR / "offline_queue.json"
SYNC_STATE_PATH = DATA_DIR / "sync_state.json"

SYNC_SERVER = os.getenv("SYNC_SERVER", "http://127.0.0.1:8000")
AGENT_CODE = os.getenv("AGENT_CODE", "agent-001")
AGENT_PASSWORD = os.getenv("AGENT_PASSWORD", "password")
SYNC_AES_KEY_BASE64 = os.getenv("SYNC_AES_KEY_BASE64", "")


def _read_queue() -> list[dict[str, Any]]:
    if not QUEUE_PATH.exists():
        return []
    try:
        return json.loads(QUEUE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return []


def _write_queue(queue: list[dict[str, Any]]) -> None:
    QUEUE_PATH.write_text(json.dumps(queue, ensure_ascii=False, indent=2), encoding="utf-8")


def enqueue(event_type: str, payload: Dict[str, Any]) -> None:
    queue = _read_queue()
    queue.append({
        "event_type": event_type,
        "payload": payload,
        "ts": datetime.utcnow().isoformat(),
    })
    _write_queue(queue)


def _load_state() -> dict[str, Any]:
    if not SYNC_STATE_PATH.exists():
        return {"last_download": "1970-01-01T00:00:00", "last_upload_products": "1970-01-01T00:00:00", "last_upload_customers": "1970-01-01T00:00:00"}
    try:
        return json.loads(SYNC_STATE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {"last_download": "1970-01-01T00:00:00", "last_upload_products": "1970-01-01T00:00:00", "last_upload_customers": "1970-01-01T00:00:00"}


def _save_state(state: dict[str, Any]) -> None:
    SYNC_STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def _get_token() -> str:
    try:
        r = requests.post(f"{SYNC_SERVER}/auth/login", json={"agent_code": AGENT_CODE, "password": AGENT_PASSWORD}, timeout=5)
        r.raise_for_status()
        return r.json()["access_token"]
    except Exception:
        return ""


def _encrypt_payload(data: dict[str, Any]) -> dict[str, str]:
    key = base64.b64decode(SYNC_AES_KEY_BASE64) if SYNC_AES_KEY_BASE64 else AESGCM.generate_key(bit_length=256)
    aes = AESGCM(key)
    nonce = os.urandom(12)
    pt = json.dumps(data).encode("utf-8")
    ptz = gzip.compress(pt)
    ct = aes.encrypt(nonce, ptz, None)
    tag = ct[-16:]
    body = ct[:-16]
    return {
        "nonce": base64.b64encode(nonce).decode(),
        "ciphertext": base64.b64encode(body).decode(),
        "tag": base64.b64encode(tag).decode(),
    }


def _collect_changes(session) -> tuple[list[dict], list[dict]]:
    state = _load_state()
    since_p = state.get("last_upload_products", "1970-01-01T00:00:00")
    since_c = state.get("last_upload_customers", "1970-01-01T00:00:00")

    prod_rows = session.execute(select(Product)).scalars().all()
    products: list[dict] = []
    for p in prod_rows:
        if not p.updated_at or p.updated_at.isoformat() <= since_p:
            continue
        if not p.external_id:
            p.external_id = f"{AGENT_CODE}-p-{p.id}"
        products.append({
            "external_id": p.external_id,
            "name": p.name,
            "price": float(p.price),
            "cost_price": float(p.cost_price or 0),
            "stock": int(p.stock),
            "updated_at": p.updated_at.isoformat(),
            "deleted_at": p.deleted_at.isoformat() if p.deleted_at else None,
        })

    cust_rows = session.execute(select(Customer)).scalars().all()
    customers: list[dict] = []
    for c in cust_rows:
        if not c.updated_at or c.updated_at.isoformat() <= since_c:
            continue
        if not c.external_id:
            c.external_id = f"{AGENT_CODE}-c-{c.id}"
        customers.append({
            "external_id": c.external_id,
            "name": c.name,
            "email": c.email,
            "phone": c.phone,
            "updated_at": c.updated_at.isoformat(),
            "deleted_at": c.deleted_at.isoformat() if c.deleted_at else None,
        })
    return products, customers


def attempt_sync(session=None) -> bool:
    queue = _read_queue()
    token = _get_token()
    if not token:
        return False

    products = []
    customers = []
    if session is not None:
        try:
            p, c = _collect_changes(session)
            products, customers = p, c
        except Exception:
            products, customers = [], []

    sales = []
    for ev in queue:
        if ev.get("event_type") == "sale_created":
            sales.append({
                "external_id": f"{AGENT_CODE}-{ev['payload']['sale_id']}",
                "agent_code": AGENT_CODE,
                "customer_external_id": None,
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
                "items": [],
            })
        elif ev.get("event_type") == "product_archived":
            pass
        elif ev.get("event_type") == "customer_archived":
            pass

    payload = {"products": products, "customers": customers, "sales": sales}
    started = time.time()
    enc = _encrypt_payload(payload)

    try:
        r = requests.post(f"{SYNC_SERVER}/sync/upload", json=enc, headers={"Authorization": f"Bearer {token}"}, timeout=20)
        r.raise_for_status()
        duration = time.time() - started
        size_bytes = len(enc.get("ciphertext", "").encode("utf-8"))
        state = _load_state()
        now = datetime.utcnow().isoformat()
        state["last_upload_products"] = now
        state["last_upload_customers"] = now
        state["last_sync_duration_sec"] = round(duration, 3)
        state["last_sync_payload_bytes"] = size_bytes
        _save_state(state)
        _write_queue([])
        return True
    except Exception:
        return False


def attempt_sync_with_backoff(session=None, max_attempts: int = 5) -> bool:
    base_delay = 2.0
    attempt = 0
    while attempt < max_attempts:
        ok = attempt_sync(session)
        state = _load_state()
        state["last_sync_ok"] = bool(ok)
        _save_state(state)
        if ok:
            return True
        sleep_s = base_delay * (2 ** attempt) + random.uniform(0, 0.5)
        time.sleep(min(sleep_s, 60.0))
        attempt += 1
    return False