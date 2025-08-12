from __future__ import annotations

import base64
import json
import os
from datetime import datetime, timedelta
import random
import requests
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

SERVER = os.getenv("SERVER", "http://127.0.0.1:8000")
AGENT = os.getenv("AGENT", "agent-001")
PASSWORD = os.getenv("PASSWORD", "password")
KEY_B64 = os.getenv("SYNC_AES_KEY_BASE64", "")


def enc_payload(data: dict) -> dict[str, str]:
    key = base64.b64decode(KEY_B64) if KEY_B64 else AESGCM.generate_key(bit_length=256)
    aes = AESGCM(key)
    nonce = os.urandom(12)
    pt = json.dumps(data).encode()
    ct = aes.encrypt(nonce, pt, None)
    tag = ct[-16:]
    body = ct[:-16]
    return {
        "nonce": base64.b64encode(nonce).decode(),
        "ciphertext": base64.b64encode(body).decode(),
        "tag": base64.b64encode(tag).decode(),
    }


def main():
    tok = requests.post(f"{SERVER}/auth/login", json={"agent_code": AGENT, "password": PASSWORD}).json()["access_token"]
    now = datetime.utcnow()
    sales = []
    for i in range(1000):
        sales.append({
            "external_id": f"{AGENT}-test-{i}",
            "agent_code": AGENT,
            "customer_external_id": None,
            "created_at": (now - timedelta(minutes=i)).isoformat(),
            "updated_at": (now - timedelta(minutes=i)).isoformat(),
            "items": [
                {"product_external_id": "SKU-1", "quantity": random.randint(1, 5), "price": 9.99},
                {"product_external_id": "SKU-2", "quantity": random.randint(1, 3), "price": 19.99},
            ],
        })
    payload = {"products": [], "customers": [], "sales": sales}
    enc = enc_payload(payload)
    res = requests.post(f"{SERVER}/sync/upload", json=enc, headers={"Authorization": f"Bearer {tok}"})
    print(res.status_code, res.text)


if __name__ == "__main__":
    main() 