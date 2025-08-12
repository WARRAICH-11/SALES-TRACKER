from __future__ import annotations

import json
import gzip
import time
from datetime import datetime, timedelta
from typing import Annotated, Callable

from fastapi import Depends, FastAPI, HTTPException, Request, Query
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select, func, extract
from sqlalchemy.orm import Session
from jinja2 import Environment, PackageLoader, select_autoescape

from .db import Base, engine, get_session
from .models import Agent, Product, Customer, Sale, SaleItem
from .security import create_access_token, verify_token, aesgcm_decrypt
from .schemas import (
    LoginRequest, TokenResponse, EncryptedPayload, SyncUploadBody, SyncUploadResponse,
    UpsertResult, DownloadResponse, ProductIn, CustomerIn, TrendResponse, TrendPoint,
    HeatmapResponse, CategoryPieResponse, CategoryPieSlice
)

app = FastAPI(title="Sales Tracker Cloud")
Base.metadata.create_all(bind=engine)
security = HTTPBearer()

env = Environment(loader=PackageLoader("app"), autoescape=select_autoescape())

# --- Middleware: simple request timing/logging ---
@app.middleware("http")
async def log_requests(request: Request, call_next: Callable):
    start = time.time()
    response = await call_next(request)
    duration_ms = int((time.time() - start) * 1000)
    path = request.url.path
    method = request.method
    try:
        client_ip = request.client.host
    except Exception:
        client_ip = "-"
    print(f"{method} {path} {response.status_code} {duration_ms}ms ip={client_ip}")
    return response

# --- Naive in-memory rate limiting (per-IP, per minute) ---
_rate: dict[str, tuple[int,int]] = {}
RATE_LIMIT = 600  # requests/min per IP

@app.middleware("http")
async def rate_limit(request: Request, call_next: Callable):
    ip = request.client.host if request.client else "-"
    now_min = int(time.time() // 60)
    count, window = _rate.get(ip, (0, now_min))
    if window != now_min:
        count, window = 0, now_min
    count += 1
    _rate[ip] = (count, window)
    if count > RATE_LIMIT:
        return PlainTextResponse("Too Many Requests", status_code=429)
    return await call_next(request)


def get_current_agent(creds: Annotated[HTTPAuthorizationCredentials, Depends(security)], db: Session) -> Agent:
    payload = verify_token(creds.credentials)
    code = payload.get("sub")
    if not code:
        raise HTTPException(status_code=401, detail="Invalid token payload")
    agent = db.execute(select(Agent).where(Agent.code == code)).scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=401, detail="Unknown agent")
    return agent


def require_admin(creds: Annotated[HTTPAuthorizationCredentials, Depends(security)]) -> None:
    payload = verify_token(creds.credentials)
    if payload.get("sub") != "admin":
        raise HTTPException(status_code=403, detail="Admins only")


@app.get("/healthz")
def healthz() -> dict:
    return {"ok": True, "ts": datetime.utcnow().isoformat()}


@app.post("/auth/login", response_model=TokenResponse)
def login(body: LoginRequest, db: Session = Depends(get_session)):
    agent = db.execute(select(Agent).where(Agent.code == body.agent_code)).scalar_one_or_none()
    if not agent:
        agent = Agent(code=body.agent_code, password_hash="demo")
        db.add(agent)
        db.commit()
    token = create_access_token({"sub": agent.code})
    return TokenResponse(access_token=token)


@app.post("/sync/upload", response_model=SyncUploadResponse)
def sync_upload(enc: EncryptedPayload, db: Session = Depends(get_session), creds: HTTPAuthorizationCredentials = Depends(security)):
    verify_token(creds.credentials)
    try:
        raw = aesgcm_decrypt(enc.nonce, enc.ciphertext, enc.tag)
        try:
            data = json.loads(gzip.decompress(raw).decode("utf-8"))
        except Exception:
            data = json.loads(raw.decode("utf-8"))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Decryption failed: {e}")

    body = SyncUploadBody(**data)
    results: list[UpsertResult] = []
    conflicts: list[str] = []

    for p in body.products:
        existing = db.execute(select(Product).where(Product.external_id == p.external_id)).scalar_one_or_none() if p.external_id else None
        if existing:
            if p.updated_at > existing.updated_at:
                existing.name = p.name
                existing.category = p.category
                existing.price = p.price
                existing.cost_price = p.cost_price
                existing.stock = p.stock
                existing.updated_at = p.updated_at
                existing.deleted_at = p.deleted_at
                status = "updated"
            else:
                status = "skipped"
        else:
            row = Product(
                external_id=p.external_id, name=p.name, category=p.category, price=p.price, cost_price=p.cost_price,
                stock=p.stock, updated_at=p.updated_at, deleted_at=p.deleted_at
            )
            db.add(row)
            status = "inserted"
        results.append(UpsertResult(type="product", external_id=p.external_id or "", status=status))

    for c in body.customers:
        existing = db.execute(select(Customer).where(Customer.external_id == c.external_id)).scalar_one_or_none() if c.external_id else None
        if existing:
            if c.updated_at > existing.updated_at:
                existing.name = c.name
                existing.email = c.email
                existing.phone = c.phone
                existing.updated_at = c.updated_at
                existing.deleted_at = c.deleted_at
                status = "updated"
            else:
                status = "skipped"
        else:
            row = Customer(
                external_id=c.external_id, name=c.name, email=c.email, phone=c.phone,
                updated_at=c.updated_at, deleted_at=c.deleted_at
            )
            db.add(row)
            status = "inserted"
        results.append(UpsertResult(type="customer", external_id=c.external_id or "", status=status))

    for s in body.sales:
        existing = db.execute(select(Sale).where(Sale.external_id == s.external_id)).scalar_one_or_none() if s.external_id else None
        if existing:
            status = "exists"
        else:
            sale = Sale(
                external_id=s.external_id,
                agent_code=s.agent_code,
                customer_external_id=s.customer_external_id,
                created_at=s.created_at,
                updated_at=s.updated_at,
            )
            db.add(sale)
            db.flush()
            for it in s.items:
                db.add(SaleItem(sale_id=sale.id, product_external_id=it.product_external_id, quantity=it.quantity, price=it.price))
            status = "inserted"
        results.append(UpsertResult(type="sale", external_id=s.external_id or "", status=status))

    db.commit()
    return SyncUploadResponse(results=results, conflicts=conflicts, server_time=datetime.utcnow())


@app.get("/sync/download", response_model=DownloadResponse)
def sync_download(since: str, db: Session = Depends(get_session), creds: HTTPAuthorizationCredentials = Depends(security)):
    verify_token(creds.credentials)
    try:
        since_dt = datetime.fromisoformat(since)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid 'since' timestamp")
    prod = [ProductIn(external_id=p.external_id, name=p.name, category=p.category, price=float(p.price), cost_price=float(p.cost_price or 0), stock=p.stock, updated_at=p.updated_at, deleted_at=p.deleted_at) for p in db.execute(select(Product).where(Product.updated_at > since_dt)).scalars()]
    cust = [CustomerIn(external_id=c.external_id, name=c.name, email=c.email, phone=c.phone, updated_at=c.updated_at, deleted_at=c.deleted_at) for c in db.execute(select(Customer).where(Customer.updated_at > since_dt)).scalars()]
    return DownloadResponse(products=prod, customers=cust, server_time=datetime.utcnow())


@app.get("/analytics/trend", response_model=TrendResponse)
def analytics_trend(days: int = Query(90, ge=1, le=365), db: Session = Depends(get_session), _=Depends(require_admin)):
    cutoff = datetime.utcnow() - timedelta(days=days)
    rows = db.execute(
        select(
            func.date(Sale.created_at),
            func.sum(SaleItem.quantity * SaleItem.price),
            func.sum(SaleItem.quantity * (SaleItem.price - (select(Product.cost_price).where(Product.external_id == SaleItem.product_external_id).scalar_subquery()))),
        ).join(SaleItem, Sale.id == SaleItem.sale_id)
        .where(Sale.created_at >= cutoff)
        .group_by(func.date(Sale.created_at))
        .order_by(func.date(Sale.created_at))
    ).all()
    points = [TrendPoint(x=datetime.fromisoformat(d), revenue=float(r or 0), profit=float(p or 0)) for d, r, p in rows]
    return TrendResponse(points=points)


@app.get("/analytics/heatmap", response_model=HeatmapResponse)
def analytics_heatmap(db: Session = Depends(get_session), _=Depends(require_admin)):
    grid = [[0 for _ in range(24)] for _ in range(7)]
    rows = db.execute(
        select(extract('dow', Sale.created_at), extract('hour', Sale.created_at), func.count(Sale.id)).group_by(extract('dow', Sale.created_at), extract('hour', Sale.created_at))
    ).all()
    for dow, hour, cnt in rows:
        grid[int(dow)][int(hour)] = int(cnt)
    return HeatmapResponse(grid=grid)


@app.get("/analytics/category_pie", response_model=CategoryPieResponse)
def analytics_category_pie(days: int = Query(30, ge=1, le=365), db: Session = Depends(get_session), _=Depends(require_admin)):
    cutoff = datetime.utcnow() - timedelta(days=days)
    rows = db.execute(
        select(Product.category, func.sum(SaleItem.quantity * SaleItem.price))
        .join(Sale, Sale.id == SaleItem.sale_id)
        .join(Product, Product.external_id == SaleItem.product_external_id, isouter=True)
        .where(Sale.created_at >= cutoff)
        .group_by(Product.category)
    ).all()
    data = [CategoryPieSlice(category=c or 'Uncategorized', revenue=float(r or 0)) for c, r in rows]
    return CategoryPieResponse(data=data)


@app.get("/admin", response_class=HTMLResponse)
def admin_dashboard(db: Session = Depends(get_session)):
    total_sales = float(db.execute(select(func.sum(SaleItem.quantity * SaleItem.price))).scalar() or 0)
    total_orders = int(db.execute(select(func.count(Sale.id))).scalar() or 0)
    cutoff = datetime.utcnow() - timedelta(days=30)
    top_rows = db.execute(
        select(SaleItem.product_external_id, func.sum(SaleItem.quantity * SaleItem.price).label("rev"))
        .join(Sale, Sale.id == SaleItem.sale_id)
        .where(Sale.created_at >= cutoff)
        .group_by(SaleItem.product_external_id)
        .order_by(func.sum(SaleItem.quantity * SaleItem.price).desc())
        .limit(10)
    ).all()
    # Ensure admin user and embed short-lived token
    admin = db.execute(select(Agent).where(Agent.code == "admin")).scalar_one_or_none()
    if not admin:
        admin = Agent(code="admin", password_hash="demo")
        db.add(admin)
        db.commit()
    token = create_access_token({"sub": "admin"}, expires_delta=timedelta(minutes=30))
    template = env.get_template("admin.html")
    html = template.render(total_sales=total_sales, total_orders=total_orders, top_products=top_rows, api_token=token)
    return HTMLResponse(html) 