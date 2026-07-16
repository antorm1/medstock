"""SQLite data layer for MedStock.

Uses only the Python standard library (sqlite3). The database file location
is controlled by the ``DB_PATH`` environment variable and defaults to
``./medstock.db``.
"""

from __future__ import annotations

import os
import sqlite3
from datetime import datetime, time, timedelta
from typing import Any

DB_PATH = os.environ.get("DB_PATH", "./medstock.db")

# ---------------------------------------------------------------------------
# Essential medicines (inspired by the WHO Model List of Essential Medicines)
# ---------------------------------------------------------------------------
MEDICINES: list[dict[str, Any]] = [
    {
        "name": "Amoxicillin",
        "category": "Antibiotic",
        "description": "Penicillin-class antibiotic used for bacterial infections.",
    },
    {
        "name": "Metformin",
        "category": "Antidiabetic",
        "description": "First-line oral medication for type 2 diabetes.",
    },
    {
        "name": "Paracetamol",
        "category": "Analgesic",
        "description": "Pain reliever and fever reducer (acetaminophen).",
    },
    {
        "name": "Insulin (Human)",
        "category": "Antidiabetic",
        "description": "Injectable hormone for managing blood glucose in diabetes.",
    },
    {
        "name": "ORS (Oral Rehydration Salts)",
        "category": "Rehydration",
        "description": "Sugar-salt solution to treat dehydration from diarrhoea.",
    },
    {
        "name": "Ibuprofen",
        "category": "Analgesic",
        "description": "Non-steroidal anti-inflammatory pain and fever medicine.",
    },
    {
        "name": "Amoxicillin/Clavulanic acid",
        "category": "Antibiotic",
        "description": "Combination antibiotic for broader bacterial coverage.",
    },
    {
        "name": "Salbutamol inhaler",
        "category": "Respiratory",
        "description": "Bronchodilator for asthma and COPD relief.",
    },
    {
        "name": "Azithromycin",
        "category": "Antibiotic",
        "description": "Macrolide antibiotic for respiratory and other infections.",
    },
    {
        "name": "Folic acid",
        "category": "Supplement",
        "description": "B-vitamin supplement, important in pregnancy.",
    },
]

# ---------------------------------------------------------------------------
# Pharmacies across Kenya (Nairobi-focused, plus a couple of other cities)
# ---------------------------------------------------------------------------
PHARMACIES: list[dict[str, Any]] = [
    {
        "name": "CBD Pharma Care",
        "area": "Nairobi CBD",
        "lat": -1.2864,
        "lng": 36.8172,
        "hours_open": "07:00",
        "hours_close": "21:00",
    },
    {
        "name": "Kibera Health Point",
        "area": "Kibera",
        "lat": -1.3126,
        "lng": 36.7896,
        "hours_open": "08:00",
        "hours_close": "20:00",
    },
    {
        "name": "Westlands Wellness Pharmacy",
        "area": "Westlands",
        "lat": -1.2676,
        "lng": 36.8105,
        "hours_open": "07:30",
        "hours_close": "22:00",
    },
    {
        "name": "Eastleigh Meds Plus",
        "area": "Eastleigh",
        "lat": -1.2770,
        "lng": 36.8560,
        "hours_open": "08:00",
        "hours_close": "22:00",
    },
    {
        "name": "Karen Family Pharmacy",
        "area": "Karen",
        "lat": -1.3197,
        "lng": 36.7104,
        "hours_open": "08:00",
        "hours_close": "19:00",
    },
    {
        "name": "Mombasa Likoni Pharmacy",
        "area": "Mombasa",
        "lat": -4.0435,
        "lng": 39.6682,
        "hours_open": "07:00",
        "hours_close": "21:00",
    },
    {
        "name": "Kisumu Lakeside Chemist",
        "area": "Kisumu",
        "lat": -0.0917,
        "lng": 34.7680,
        "hours_open": "08:00",
        "hours_close": "20:00",
    },
]

# ---------------------------------------------------------------------------
# Seed stock. status: in_stock | low_stock | out_of_stock
# At least two medicines have an out-of-stock report somewhere.
# ---------------------------------------------------------------------------
# (medicine_index, pharmacy_index, status, price_kes, quantity)
STOCK_SEED: list[tuple[int, int, str, float, int]] = [
    (0, 0, "in_stock", 350.0, 120),   # Amoxicillin @ CBD
    (0, 1, "low_stock", 360.0, 8),    # Amoxicillin @ Kibera
    (0, 2, "in_stock", 340.0, 60),    # Amoxicillin @ Westlands
    (0, 6, "out_of_stock", 0.0, 0),   # Amoxicillin @ Kisumu  -> shortage
    (1, 0, "in_stock", 280.0, 90),    # Metformin @ CBD
    (1, 3, "in_stock", 275.0, 40),    # Metformin @ Eastleigh
    (1, 4, "low_stock", 300.0, 5),    # Metformin @ Karen
    (2, 0, "in_stock", 50.0, 300),    # Paracetamol @ CBD
    (2, 1, "in_stock", 55.0, 150),    # Paracetamol @ Kibera
    (2, 2, "low_stock", 45.0, 12),    # Paracetamol @ Westlands
    (2, 3, "in_stock", 50.0, 80),     # Paracetamol @ Eastleigh
    (3, 2, "in_stock", 1200.0, 30),   # Insulin @ Westlands
    (3, 0, "low_stock", 1250.0, 4),   # Insulin @ CBD
    (3, 5, "out_of_stock", 0.0, 0),   # Insulin @ Mombasa -> shortage
    (4, 1, "in_stock", 30.0, 200),    # ORS @ Kibera
    (4, 0, "in_stock", 28.0, 180),    # ORS @ CBD
    (4, 3, "low_stock", 32.0, 10),    # ORS @ Eastleigh
    (5, 0, "in_stock", 70.0, 100),    # Ibuprofen @ CBD
    (5, 4, "in_stock", 75.0, 50),     # Ibuprofen @ Karen
    (6, 2, "in_stock", 420.0, 45),    # Amox/Clav @ Westlands
    (6, 1, "out_of_stock", 0.0, 0),   # Amox/Clav @ Kibera -> shortage
    (7, 0, "in_stock", 650.0, 25),    # Salbutamol @ CBD
    (7, 3, "low_stock", 680.0, 6),    # Salbutamol @ Eastleigh
    (8, 2, "in_stock", 300.0, 70),    # Azithromycin @ Westlands
    (8, 5, "in_stock", 310.0, 35),    # Azithromycin @ Mombasa
    (9, 1, "in_stock", 40.0, 120),    # Folic acid @ Kibera
    (9, 4, "low_stock", 42.0, 9),     # Folic acid @ Karen
]

SHORTAGE_NOTES = {
    (0, 6): "Supplier delay; expected restock next week.",
    (3, 5): "Cold-chain stock-out, urgent for diabetic patients.",
    (6, 1): "Temporarily out, pharmacy awaiting delivery.",
}


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _parse_time(value: str) -> time:
    h, m = value.split(":")
    return time(int(h), int(m))


def init_db() -> None:
    """Create tables (if needed) and seed data on first run."""
    conn = _connect()
    try:
        cur = conn.cursor()
        cur.executescript(
            """
            CREATE TABLE IF NOT EXISTS medicines (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                category TEXT,
                description TEXT
            );

            CREATE TABLE IF NOT EXISTS pharmacies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                area TEXT,
                lat REAL,
                lng REAL,
                hours_open TEXT,
                hours_close TEXT
            );

            CREATE TABLE IF NOT EXISTS stock (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pharmacy_id INTEGER NOT NULL,
                medicine_id INTEGER NOT NULL,
                status TEXT NOT NULL,
                price REAL,
                quantity INTEGER,
                updated_at TEXT,
                updated_by TEXT,
                UNIQUE(pharmacy_id, medicine_id)
            );

            CREATE TABLE IF NOT EXISTS shortages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pharmacy_id INTEGER NOT NULL,
                medicine_id INTEGER NOT NULL,
                reported_at TEXT,
                notes TEXT,
                resolved INTEGER DEFAULT 0
            );

            CREATE INDEX IF NOT EXISTS idx_stock_pharm ON stock(pharmacy_id);
            CREATE INDEX IF NOT EXISTS idx_stock_med ON stock(medicine_id);
            """
        )

        # Seed only if empty.
        if cur.execute("SELECT COUNT(*) FROM medicines").fetchone()[0] == 0:
            cur.executemany(
                "INSERT INTO medicines (name, category, description) VALUES (?, ?, ?)",
                [(m["name"], m["category"], m["description"]) for m in MEDICINES],
            )
            cur.executemany(
                "INSERT INTO pharmacies (name, area, lat, lng, hours_open, hours_close) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                [
                    (
                        p["name"],
                        p["area"],
                        p["lat"],
                        p["lng"],
                        p["hours_open"],
                        p["hours_close"],
                    )
                    for p in PHARMACIES
                ],
            )
            now = datetime.utcnow().isoformat()
            for med_i, ph_i, status, price, qty in STOCK_SEED:
                ph_id = ph_i + 1
                med_id = med_i + 1
                cur.execute(
                    "INSERT INTO stock (pharmacy_id, medicine_id, status, price, quantity, "
                    "updated_at, updated_by) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (ph_id, med_id, status, price, qty, now, "seed"),
                )
                if status == "out_of_stock":
                    note = SHORTAGE_NOTES.get((med_i, ph_i), "Reported out of stock.")
                    cur.execute(
                        "INSERT INTO shortages (pharmacy_id, medicine_id, reported_at, notes) "
                        "VALUES (?, ?, ?, ?)",
                        (ph_id, med_id, now, note),
                    )

        conn.commit()
    finally:
        conn.close()


def get_conn() -> sqlite3.Connection:
    return _connect()
