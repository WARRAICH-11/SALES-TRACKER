from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import List, Tuple

import numpy as np
import pandas as pd

try:
    import onnxruntime as ort  # type: ignore
except Exception:  # pragma: no cover
    ort = None  # type: ignore

try:
    from statsmodels.tsa.arima.model import ARIMA
except Exception:  # pragma: no cover
    ARIMA = None  # type: ignore

from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.ai.config import FORECAST_HORIZON_DAYS, FORECAST_ONNX_PATH
from app.data.models import Sale, SaleItem


@dataclass
class ForecastResult:
    dates: list[date]
    values: list[float]


def _load_daily_sales(session: Session) -> pd.Series:
    stmt = (
        select(func.date(Sale.created_at), func.sum(SaleItem.quantity * SaleItem.price))
        .join(SaleItem, Sale.id == SaleItem.sale_id)
        .group_by(func.date(Sale.created_at))
        .order_by(func.date(Sale.created_at))
    )
    rows = [(datetime.strptime(d, "%Y-%m-%d").date(), float(v or 0)) for d, v in session.execute(stmt)]
    if not rows:
        today = date.today()
        return pd.Series([0.0], index=[pd.to_datetime(today)])
    idx = pd.to_datetime([d for d, _ in rows])
    vals = [v for _, v in rows]
    return pd.Series(vals, index=idx)


def train_arima_and_forecast(session: Session, horizon_days: int = FORECAST_HORIZON_DAYS) -> ForecastResult:
    series = _load_daily_sales(session)
    series = series.asfreq("D").fillna(0.0)
    if ARIMA is None:
        # Fallback naive forecast: last value repeated
        last = float(series.iloc[-1]) if len(series) else 0.0
        future_idx = pd.date_range(series.index[-1] + pd.Timedelta(days=1), periods=horizon_days, freq="D")
        return ForecastResult(dates=[d.date() for d in future_idx], values=[last] * horizon_days)

    model = ARIMA(series, order=(2, 1, 2))
    fitted = model.fit()
    forecast = fitted.forecast(steps=horizon_days)
    return ForecastResult(dates=[d.date() for d in forecast.index], values=[float(v) for v in forecast.values])


def run_onnx_forecast(input_series: pd.Series, horizon_days: int = FORECAST_HORIZON_DAYS) -> ForecastResult:
    if ort is None or not Path(FORECAST_ONNX_PATH).exists():
        # Not available; return empty result to signal caller to use ARIMA
        return ForecastResult(dates=[], values=[])
    sess = ort.InferenceSession(str(FORECAST_ONNX_PATH))
    arr = input_series.values.astype(np.float32)[None, :]
    out = sess.run(None, {sess.get_inputs()[0].name: arr})[0][0]
    last_date = input_series.index[-1].date()
    dates = [last_date + timedelta(days=i + 1) for i in range(horizon_days)]
    return ForecastResult(dates=dates, values=[float(v) for v in out[:horizon_days]]) 