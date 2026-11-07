#!/usr/bin/env bash
set -e

echo "========================================================"
echo "Multimodal Industrial Inspection Agent - Launcher"
echo "========================================================"

if command -v python3 >/dev/null 2>&1; then
    PY_BIN="python3"
elif command -v python >/dev/null 2>&1; then
    PY_BIN="python"
else
    echo "[ERROR] Python 3 was not found in your PATH."
    echo "Please install Python 3.10 or higher."
    exit 1
fi

if [ ! -d ".venv" ]; then
    echo "[INFO] Creating virtual environment in .venv..."
    $PY_BIN -m venv .venv
fi

echo "[INFO] Activating virtual environment..."
source .venv/bin/activate

if [ ! -f ".env" ] && [ -f ".env.example" ]; then
    echo "[INFO] Initializing .env configuration from .env.example..."
    cp .env.example .env
fi

echo "[INFO] Ensuring core lightweight dependencies are installed..."
pip install -r backend/requirements.txt --quiet

echo "========================================================"
echo "Service starting at http://localhost:8000"
echo "Open http://localhost:8000 in your web browser."
echo "Press Ctrl+C to terminate the server."
echo "========================================================"

python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
