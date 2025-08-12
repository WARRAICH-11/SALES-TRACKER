from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple

import numpy as np

try:
    import faiss  # type: ignore
except Exception:  # pragma: no cover
    faiss = None  # type: ignore

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.embeddings import Embeddings
from app.ai.llm import LocalLLM
from app.ai.config import FAISS_INDEX_PATH, DOCSTORE_PATH
from app.ai.cache import get_cached_answer, set_cached_answer
from app.data.models import Product, Customer, Sale, SaleItem


@dataclass
class RetrievedChunk:
    text: str
    score: float


SCHEMA_HINT = (
    "Tables: products(id, external_id, name, price, cost_price, stock, updated_at, deleted_at), customers(id, external_id, name, email, phone, updated_at, deleted_at), "
    "sales(id, customer_id, created_at), sale_items(id, sale_id, product_id, quantity, price).\n"
    "Revenue = sum(quantity*price). Profit = sum(quantity*(price-cost_price)). Margin = profit/revenue.\n"
    "Dates are UTC timestamps in sales.created_at."
)


class SalesRAG:
    def __init__(self, session: Session) -> None:
        if faiss is None:
            raise RuntimeError("faiss is not installed. Install faiss-cpu for vector search.")
        self.session = session
        self.embedder = Embeddings()
        self.llm = LocalLLM()
        self.index = None
        self.doc_texts: list[str] = []

        self._load_index()

    def _load_index(self) -> None:
        if FAISS_INDEX_PATH.exists() and Path(DOCSTORE_PATH).exists():
            self.index = faiss.read_index(str(FAISS_INDEX_PATH))
            self.doc_texts = json.loads(Path(DOCSTORE_PATH).read_text(encoding="utf-8"))
        else:
            self.rebuild_index()

    def rebuild_index(self) -> None:
        """Rebuild the entire FAISS index from the database."""
        rows: list[str] = []

        # Products
        for p in self.session.execute(select(Product)).scalars():
            rows.append(f"PRODUCT id={p.id} name={p.name} price={float(p.price):.2f} stock={p.stock}")

        # Customers
        for c in self.session.execute(select(Customer)).scalars():
            rows.append(f"CUSTOMER id={c.id} name={c.name} email={c.email or ''} phone={c.phone or ''}")

        # Sales and items
        stmt = (
            select(Sale.id, Sale.created_at, Product.name, SaleItem.quantity, SaleItem.price)
            .join(SaleItem, Sale.id == SaleItem.sale_id)
            .join(Product, Product.id == SaleItem.product_id)
            .order_by(Sale.created_at.desc())
        )
        for sid, created, pname, qty, price in self.session.execute(stmt):
            rows.append(
                f"SALE id={sid} created_at={created.isoformat()} product={pname} qty={qty} price={float(price):.2f}"
            )

        if not rows:
            rows = ["No data yet. Products, customers, and sales will appear here when created."]

        # Generate embeddings and convert to numpy array
        embeds = self.embedder.encode(rows)
        embeds_array = np.array(embeds, dtype=np.float32)  # Ensure proper array conversion
        
        if embeds_array.size == 0:
            self.index = None
            return
            
        dim = embeds_array.shape[1]
        self.index = faiss.IndexFlatIP(dim)
        self.index.add(embeds_array)  # Add the numpy array

        FAISS_INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
        faiss.write_index(self.index, str(FAISS_INDEX_PATH))
        Path(DOCSTORE_PATH).write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
        self.doc_texts = rows

    def retrieve(self, query: str, k: int = 8) -> list[RetrievedChunk]:
        if self.index is None:
            return []
        qv = self.embedder.encode([query]).astype(np.float32)
        sims, idxs = self.index.search(qv, k)
        out: list[RetrievedChunk] = []
        for score, idx in zip(sims[0], idxs[0]):
            if idx < 0 or idx >= len(self.doc_texts):
                continue
            out.append(RetrievedChunk(text=self.doc_texts[idx], score=float(score)))
        return out

    def answer(self, question: str) -> str:
        cached = get_cached_answer(question)
        if cached:
            return cached
        chunks = self.retrieve(question, k=8)
        context = "\n".join(c.text for c in chunks)
        prompt = (
            "You are a helpful retail analytics assistant. Answer using the context only.\n"
            "If numbers are required, compute from the provided rows. Be concise.\n"
            f"Schema:\n{SCHEMA_HINT}\n"
            f"Context:\n{context}\n\n"
            f"Question: {question}\n"
            "Answer:"
        )
        ans = self.llm.infer(prompt)
        set_cached_answer(question, ans)
        return ans 