from __future__ import annotations

import base64
import os
from datetime import datetime, timedelta
from typing import Any, Dict

import jwt
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from fastapi import HTTPException, status

SECRET_KEY = os.getenv("SECRET_KEY", "change-me")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 12

SYNC_AES_KEY_BASE64 = os.getenv("SYNC_AES_KEY_BASE64", "")
if not SYNC_AES_KEY_BASE64:
    # Dev fallback (NOT for production)
    SYNC_AES_KEY = AESGCM.generate_key(bit_length=256)
else:
    SYNC_AES_KEY = base64.b64decode(SYNC_AES_KEY_BASE64)


def create_access_token(data: dict[str, Any], expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def verify_token(token: str) -> dict[str, Any]:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.PyJWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")


def aesgcm_decrypt(nonce_b64: str, ciphertext_b64: str, tag_b64: str) -> bytes:
    aesgcm = AESGCM(SYNC_AES_KEY)
    nonce = base64.b64decode(nonce_b64)
    ct = base64.b64decode(ciphertext_b64)
    tag = base64.b64decode(tag_b64)
    # AESGCM expects ct+tag concatenated
    return aesgcm.decrypt(nonce, ct + tag, None)


def aesgcm_encrypt(plaintext: bytes) -> dict[str, str]:
    aesgcm = AESGCM(SYNC_AES_KEY)
    nonce = os.urandom(12)
    ct = aesgcm.encrypt(nonce, plaintext, None)
    # split tag (last 16 bytes)
    tag = ct[-16:]
    body = ct[:-16]
    return {
        "nonce": base64.b64encode(nonce).decode(),
        "ciphertext": base64.b64encode(body).decode(),
        "tag": base64.b64encode(tag).decode(),
    } 