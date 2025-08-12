from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from app.ai.config import CACHE_PATH


@dataclass
class CacheEntry:
    question: str
    answer: str
    ts: str
    hits: int


def _load_cache() -> dict[str, CacheEntry]:
    if not Path(CACHE_PATH).exists():
        return {}
    try:
        raw = json.loads(Path(CACHE_PATH).read_text(encoding="utf-8"))
        return {k: CacheEntry(**v) for k, v in raw.items()}
    except Exception:
        return {}


def _save_cache(store: dict[str, CacheEntry]) -> None:
    Path(CACHE_PATH).write_text(
        json.dumps({k: vars(v) for k, v in store.items()}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def get_cached_answer(question: str, max_age_minutes: int = 60) -> Optional[str]:
    store = _load_cache()
    key = question.strip().lower()
    if key not in store:
        return None
    entry = store[key]
    try:
        ts = datetime.fromisoformat(entry.ts)
        if datetime.utcnow() - ts > timedelta(minutes=max_age_minutes):
            return None
    except Exception:
        return None
    entry.hits += 1
    store[key] = entry
    _save_cache(store)
    return entry.answer


def set_cached_answer(question: str, answer: str) -> None:
    store = _load_cache()
    key = question.strip().lower()
    store[key] = CacheEntry(question=question, answer=answer, ts=datetime.utcnow().isoformat(), hits=1)
    _save_cache(store) 