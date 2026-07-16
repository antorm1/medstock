"""MedStock FastAPI application.

Essential-medicine stockout tracker & pharmacy finder.

Run with:  uvicorn app.main:app --reload --port 8000
"""

from __future__ import annotations

import math
import os
from datetime import datetime, time
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from . import db
from .models import (
    FindResult,
    Medicine,
    Pharmacy,
    ShortageReport,
    Stats,
    StockEntry,
    StockUpdate,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Great-circle distance between two coordinates in kilometres."""
    r = 6371.0088  # mean Earth radius (km)
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lng2 - lng1)
    a = (
        math.sin(dphi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    )
    return 2 * r * math.asin(math.sqrt(a))


def _parse_time(value: Optional[str]) -> Optional[time]:
    if not value:
        return None
    try:
        h, m = value.split(":")
        return time(int(h), int(m))
    except (ValueError, AttributeError):
        return None


def is_open_now(hours_open: Optional[str], hours_close: Optional[str]) -> bool:
    """Return True if the current local time falls within opening hours.

    Opening hours wrap midnight (e.g. 22:00 -> 06:00) when close < open.
    """
    open_t = _parse_time(hours_open)
    close_t = _parse_time(hours_close)
    if open_t is None or close_t is None:
        return False
    now = datetime.now().time()
    if open_t <= close_t:
        return open_t <= now <= close_t
    # wraps midnight
    return now >= open_t or now <= close_t


def _fetch_pharmacy(conn, pharmacy_id: int) -> Optional[dict]:
    row = conn.execute(
        "SELECT * FROM pharmacies WHERE id = ?", (pharmacy_id,)
    ).fetchone()
    return dict(row) if row else None


def _fetch_medicine(conn, medicine_id: int) -> Optional[dict]:
    row = conn.execute(
        "SELECT * FROM medicines WHERE id = ?", (medicine_id,)
    ).fetchone()
    return dict(row) if row else None


# ---------------------------------------------------------------------------
# App + startup
# ---------------------------------------------------------------------------
app = FastAPI(title="MedStock", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def init_db() -> None:
    db.init_db()


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "medstock", "time": datetime.utcnow().isoformat()}


@app.get("/medicines", response_model=list[Medicine])
def get_medicines() -> list[dict]:
    conn = db.get_conn()
    try:
        rows = conn.execute(
            "SELECT id, name, category, description FROM medicines ORDER BY name"
        ).fetchall()
    finally:
        conn.close()
    return [dict(r) for r in rows]


@app.get("/pharmacies", response_model=list[Pharmacy])
def get_pharmacies() -> list[dict]:
    conn = db.get_conn()
    try:
        rows = conn.execute(
            "SELECT id, name, area, lat, lng, hours_open, hours_close FROM pharmacies "
            "ORDER BY name"
        ).fetchall()
    finally:
        conn.close()
    return [dict(r) for r in rows]


@app.get("/stock", response_model=list[StockEntry])
def get_stock(
    medicine_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    pharmacy_id: Optional[int] = Query(None),
) -> list[dict]:
    conn = db.get_conn()
    try:
        clause = []
        params: list = []
        if medicine_id is not None:
            clause.append("s.medicine_id = ?")
            params.append(medicine_id)
        if status is not None:
            clause.append("s.status = ?")
            params.append(status)
        if pharmacy_id is not None:
            clause.append("s.pharmacy_id = ?")
            params.append(pharmacy_id)
        where = (" WHERE " + " AND ".join(clause)) if clause else ""
        rows = conn.execute(
            """
            SELECT s.id, s.pharmacy_id, s.medicine_id, s.status, s.price, s.quantity,
                   s.updated_at, s.updated_by,
                   m.name AS medicine_name, p.name AS pharmacy_name, p.area,
                   p.hours_open, p.hours_close
            FROM stock s
            JOIN medicines m ON m.id = s.medicine_id
            JOIN pharmacies p ON p.id = s.pharmacy_id
            """
            + where
            + " ORDER BY m.name, p.name"
        ).fetchall()

        result = []
        for r in rows:
            d = dict(r)
            d["open_now"] = is_open_now(d.pop("hours_open"), d.pop("hours_close"))
            result.append(d)
        return result
    finally:
        conn.close()


@app.get("/find", response_model=list[FindResult])
def find(
    medicine_id: int = Query(...),
    lat: Optional[float] = Query(None),
    lng: Optional[float] = Query(None),
    radius_km: float = Query(50.0),
) -> list[dict]:
    conn = db.get_conn()
    try:
        med = _fetch_medicine(conn, medicine_id)
        if med is None:
            raise HTTPException(status_code=404, detail="medicine not found")

        rows = conn.execute(
            """
            SELECT s.pharmacy_id, s.status, s.price, s.quantity,
                   p.name AS pharmacy_name, p.area, p.lat, p.lng,
                   p.hours_open, p.hours_close
            FROM stock s
            JOIN pharmacies p ON p.id = s.pharmacy_id
            WHERE s.medicine_id = ? AND s.status != 'out_of_stock'
            """,
            (medicine_id,),
        ).fetchall()

        if not rows:
            # Nothing in stock anywhere: report (with status info) so the user
            # still gets useful data.
            all_rows = conn.execute(
                """
                SELECT s.pharmacy_id, s.status, s.price, s.quantity,
                       p.name AS pharmacy_name, p.area, p.lat, p.lng,
                       p.hours_open, p.hours_close
                FROM stock s
                JOIN pharmacies p ON p.id = s.pharmacy_id
                WHERE s.medicine_id = ?
                """,
                (medicine_id,),
            ).fetchall()
            out = []
            for r in all_rows:
                d = dict(r)
                if d["lat"] is not None and d["lng"] is not None and lat is not None and lng is not None:
                    d["distance_km"] = round(
                        haversine_km(lat, lng, d["lat"], d["lng"]), 2
                    )
                else:
                    d["distance_km"] = float("inf")
                d["open_now"] = is_open_now(d.pop("hours_open"), d.pop("hours_close"))
                out.append(d)
            out.sort(key=lambda x: x["distance_km"])
            return out

        out = []
        for r in rows:
            d = dict(r)
            if d["lat"] is not None and d["lng"] is not None and lat is not None and lng is not None:
                d["distance_km"] = round(
                    haversine_km(lat, lng, d["lat"], d["lng"]), 2
                )
            else:
                d["distance_km"] = float("inf")
            d["open_now"] = is_open_now(d.pop("hours_open"), d.pop("hours_close"))
            out.append(d)

        # Sort by distance. If the user supplied coordinates, filter to radius
        # and, if nothing is within radius, fall back to the nearest (with info).
        out.sort(key=lambda x: x["distance_km"])
        if lat is not None and lng is not None:
            in_radius = [x for x in out if x["distance_km"] <= radius_km]
            if in_radius:
                return in_radius
        return out
    finally:
        conn.close()


@app.post("/stock", response_model=StockEntry)
def upsert_stock(payload: StockUpdate) -> dict:
    conn = db.get_conn()
    try:
        if _fetch_pharmacy(conn, payload.pharmacy_id) is None:
            raise HTTPException(status_code=404, detail="pharmacy not found")
        if _fetch_medicine(conn, payload.medicine_id) is None:
            raise HTTPException(status_code=404, detail="medicine not found")

        now = datetime.utcnow().isoformat()
        existing = conn.execute(
            "SELECT id FROM stock WHERE pharmacy_id = ? AND medicine_id = ?",
            (payload.pharmacy_id, payload.medicine_id),
        ).fetchone()

        if existing:
            conn.execute(
                """
                UPDATE stock
                SET status = ?, price = ?, quantity = ?, updated_at = ?, updated_by = ?
                WHERE pharmacy_id = ? AND medicine_id = ?
                """,
                (
                    payload.status,
                    payload.price,
                    payload.quantity,
                    now,
                    payload.updated_by,
                    payload.pharmacy_id,
                    payload.medicine_id,
                ),
            )
            stock_id = existing["id"]
        else:
            cur = conn.execute(
                """
                INSERT INTO stock
                (pharmacy_id, medicine_id, status, price, quantity, updated_at, updated_by)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    payload.pharmacy_id,
                    payload.medicine_id,
                    payload.status,
                    payload.price,
                    payload.quantity,
                    now,
                    payload.updated_by,
                ),
            )
            stock_id = cur.lastrowid

        # Auto-create a shortage report when marked out of stock.
        if payload.status == "out_of_stock":
            conn.execute(
                """
                INSERT INTO shortages (pharmacy_id, medicine_id, reported_at, notes)
                VALUES (?, ?, ?, ?)
                """,
                (
                    payload.pharmacy_id,
                    payload.medicine_id,
                    now,
                    "Reported out of stock by pharmacist.",
                ),
            )

        conn.commit()
        row = conn.execute(
            "SELECT id, pharmacy_id, medicine_id, status, price, quantity, "
            "updated_at, updated_by FROM stock WHERE id = ?",
            (stock_id,),
        ).fetchone()
        return dict(row)
    finally:
        conn.close()


@app.get("/shortages", response_model=list[ShortageReport])
def get_shortages(limit: int = Query(50)) -> list[dict]:
    conn = db.get_conn()
    try:
        rows = conn.execute(
            """
            SELECT sh.id, sh.pharmacy_id, sh.medicine_id, sh.reported_at, sh.notes,
                   sh.resolved, m.name AS medicine_name, p.name AS pharmacy_name,
                   p.area
            FROM shortages sh
            JOIN medicines m ON m.id = sh.medicine_id
            JOIN pharmacies p ON p.id = sh.pharmacy_id
            ORDER BY sh.reported_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


@app.get("/stats", response_model=Stats)
def get_stats() -> dict:
    conn = db.get_conn()
    try:
        medicines = conn.execute("SELECT COUNT(*) FROM medicines").fetchone()[0]
        pharmacies = conn.execute("SELECT COUNT(*) FROM pharmacies").fetchone()[0]
        shortages = conn.execute(
            "SELECT COUNT(*) FROM shortages WHERE resolved = 0"
        ).fetchone()[0]
        in_stock = conn.execute(
            "SELECT COUNT(*) FROM stock WHERE status = 'in_stock'"
        ).fetchone()[0]
        return {
            "medicines": medicines,
            "pharmacies": pharmacies,
            "shortages": shortages,
            "in_stock": in_stock,
        }
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Static frontend serving (used when containerised)
# ---------------------------------------------------------------------------
_STATIC_DIR = os.environ.get("STATIC_DIR", os.path.join(os.path.dirname(__file__), "..", "static"))


@app.get("/")
def index() -> FileResponse:
    index_path = os.path.join(_STATIC_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return JSONResponse(
        {
            "service": "medstock",
            "message": "API is running. Frontend build not found. "
            "Serve the built 'dist' as static files.",
        }
    )


def _mount_static() -> None:
    assets = os.path.join(_STATIC_DIR, "assets")
    if os.path.isdir(assets):
        app.mount("/assets", StaticFiles(directory=assets), name="assets")


_mount_static()
