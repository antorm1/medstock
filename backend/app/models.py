"""Pydantic models for MedStock API requests and responses."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Domain entities
# ---------------------------------------------------------------------------
class Medicine(BaseModel):
    id: int
    name: str
    category: Optional[str] = None
    description: Optional[str] = None


class Pharmacy(BaseModel):
    id: int
    name: str
    area: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    hours_open: Optional[str] = None
    hours_close: Optional[str] = None


class StockEntry(BaseModel):
    id: int
    pharmacy_id: int
    medicine_id: int
    status: str
    price: Optional[float] = None
    quantity: Optional[int] = None
    updated_at: Optional[str] = None
    updated_by: Optional[str] = None
    # Joined helper fields (populated by some endpoints)
    medicine_name: Optional[str] = None
    pharmacy_name: Optional[str] = None
    area: Optional[str] = None
    open_now: Optional[bool] = None


class ShortageReport(BaseModel):
    id: int
    pharmacy_id: int
    medicine_id: int
    reported_at: Optional[str] = None
    notes: Optional[str] = None
    resolved: int = 0
    medicine_name: Optional[str] = None
    pharmacy_name: Optional[str] = None
    area: Optional[str] = None


# ---------------------------------------------------------------------------
# Request bodies
# ---------------------------------------------------------------------------
class StockUpdate(BaseModel):
    pharmacy_id: int
    medicine_id: int
    status: str = Field(..., pattern="^(in_stock|low_stock|out_of_stock)$")
    price: Optional[float] = None
    quantity: Optional[int] = None
    updated_by: Optional[str] = "pharmacist"


# ---------------------------------------------------------------------------
# Derived / response helpers
# ---------------------------------------------------------------------------
class FindResult(BaseModel):
    pharmacy_id: int
    pharmacy_name: str
    area: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    distance_km: float
    status: str
    price: Optional[float] = None
    quantity: Optional[int] = None
    open_now: bool


class Stats(BaseModel):
    medicines: int
    pharmacies: int
    shortages: int
    in_stock: int
