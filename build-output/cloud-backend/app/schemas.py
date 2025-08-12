from __future__ import annotations

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    agent_code: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class EncryptedPayload(BaseModel):
    nonce: str
    ciphertext: str
    tag: str


class ProductIn(BaseModel):
    external_id: Optional[str] = None
    name: str
    category: Optional[str] = None
    price: float
    cost_price: Optional[float] = None
    stock: int
    updated_at: datetime
    deleted_at: Optional[datetime] = None


class CustomerIn(BaseModel):
    external_id: Optional[str] = None
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    updated_at: datetime
    deleted_at: Optional[datetime] = None


class SaleItemIn(BaseModel):
    product_external_id: str
    quantity: int
    price: float


class SaleIn(BaseModel):
    external_id: Optional[str] = None
    agent_code: str
    customer_external_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    items: List[SaleItemIn] = Field(default_factory=list)


class SyncUploadBody(BaseModel):
    products: List[ProductIn] = Field(default_factory=list)
    customers: List[CustomerIn] = Field(default_factory=list)
    sales: List[SaleIn] = Field(default_factory=list)


class UpsertResult(BaseModel):
    type: str
    external_id: str
    status: str


class SyncUploadResponse(BaseModel):
    results: List[UpsertResult]
    conflicts: List[str] = Field(default_factory=list)
    server_time: datetime


class DownloadResponse(BaseModel):
    products: List[ProductIn]
    customers: List[CustomerIn]
    server_time: datetime


class TrendPoint(BaseModel):
    x: datetime
    revenue: float
    profit: float


class TrendResponse(BaseModel):
    points: List[TrendPoint]


class HeatmapResponse(BaseModel):
    # 7x24 matrix rows=weekday(0..6) cols=hour(0..23)
    grid: List[List[int]]


class CategoryPieSlice(BaseModel):
    category: str
    revenue: float


class CategoryPieResponse(BaseModel):
    data: List[CategoryPieSlice] 