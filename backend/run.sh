#!/usr/bin/env bash
# Run the MedStock FastAPI backend.
set -e
cd "$(dirname "$0")"
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
