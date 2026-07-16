# Antorm • MedStock

**Essential-medicine stockout tracker & pharmacy finder** for low-bandwidth, mobile-first contexts.

Patients find which nearby pharmacy has a medicine in stock. Pharmacists report shortages in seconds. Built to shrink medicine access gaps — critical in 2026.

> Part of the **Antorm** open-source app suite by [@antorm1](https://github.com/antorm1).

---

## The problem

In many regions, patients travel to multiple pharmacies before finding a medicine — wasting time, money, and, for chronic conditions like diabetes, risking health. Stock information is fragmented and invisible until you arrive.

**MedStock** makes stock visibility a shared, real-time resource:
- A patient types a medicine name and sees nearby pharmacies that **have it in stock**, sorted by distance, with price and "open now" status.
- A pharmacist taps a few fields to report what they have (or don't), and an out-of-stock report is created automatically.

## Features

- 🔎 **Medicine search** — find Amoxicillin, Metformin, Paracetamol, Insulin, ORS and more.
- 📍 **Nearest pharmacy with stock** — haversine distance from your geolocation or entered lat/lng; the nearest in-stock pharmacy is highlighted.
- 🟢 **Status badges** — In stock / Low / Out, with price and last-updated time.
- 🕒 **Open-now indicator** — respects each pharmacy's opening hours.
- 💊 **Pharmacist portal** — simple form to update stock (demo, no auth — see note).
- 🚨 **Shortage list** — recent out-of-stock reports with location.
- 📊 **Stats dashboard** — medicines tracked, pharmacies, active shortages, in-stock entries.
- 🚑 **Health note** — always reminds users to contact emergency services if needed.
- 📱 **Mobile-first** — lightweight, works on low-bandwidth connections.
- 🐳 **Self-contained** — single Docker image serves API + static frontend.

## Tech stack

- **Backend:** Python · FastAPI · SQLite (stdlib `sqlite3`, no ORM)
- **Frontend:** React · TypeScript · Vite · Tailwind CSS · lucide-react
- **Deploy:** Docker (multi-stage) + docker-compose

## Quick start (local dev)

### Backend
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```
API docs at http://localhost:8000/docs

### Frontend
```bash
cd frontend
npm install
npm run dev
```
Open http://localhost:5175 (Vite). It calls the backend at `http://localhost:8000` by default; override with `VITE_API`.

## Environment variables

See `.env.example`:

| Variable   | Default             | Description                                  |
|------------|---------------------|----------------------------------------------|
| `DB_PATH`  | `./medstock.db`     | Path to the SQLite database file.            |
| `VITE_API` | `http://localhost:8000` | Backend URL used by the frontend (build-time). |
| `PORT`     | `8000`              | Port the containerised app listens on.       |

## Docker

```bash
docker build -t medstock .
docker run -e DB_PATH=/data/medstock.db -v $(pwd)/data:/data -p 8000:8000 medstock
```

Or with compose:

```bash
docker compose up --build
```

Then open http://localhost:8000 — the container serves both the API and the built frontend.

## API

| Method | Endpoint                                  | Description                                            |
|--------|-------------------------------------------|--------------------------------------------------------|
| GET    | `/health`                                 | Liveness check.                                        |
| GET    | `/medicines`                              | List medicines (id, name, category, description).      |
| GET    | `/pharmacies`                             | List pharmacies (id, name, area, lat, lng, hours).     |
| GET    | `/stock?medicine_id=&status=&pharmacy_id=` | Stock entries joined with names + `open_now`.        |
| GET    | `/find?medicine_id=&lat=&lng=&radius_km=` | Pharmacies with stock, sorted by distance.             |
| POST   | `/stock`                                  | Upsert a stock entry; auto-creates shortage if `out_of_stock`. |
| GET    | `/shortages?limit=50`                     | Recent out-of-stock reports.                           |
| GET    | `/stats`                                  | `{medicines, pharmacies, shortages, in_stock}`.        |

### Example
```bash
curl "http://localhost:8000/find?medicine_id=1&lat=-1.2921&lng=36.8219"
```

## Demo data

The database seeds on first run with ~10 essential medicines (WHO-style list), ~7 pharmacies across Nairobi + Mombasa + Kisumu, and varied stock — including at least two out-of-stock medicines (Amoxicillin in Kisumu, Insulin in Mombasa, Amoxicillin/Clavulanic acid in Kibera).

> **Note:** The pharmacist portal has **no authentication** — it is a demonstration. Production deployments must require pharmacist login before accepting stock updates.

## License

MIT © Antorm. See [LICENSE](./LICENSE).
