# Multimodal Industrial Inspection Agent

A multimodal intelligent inspection agent for industrial quality inspection scenarios. The system combines images, inspection standard documents, and structured sensor data to perform defect identification, standards-based evidence retrieval, risk grading, report generation, and human review recommendations.

## One-Sentence Positioning

Multimodal_Industrial_Inspection_Agent is a multimodal intelligent inspection agent for industrial quality inspection. It combines images, videos, textual standards, and sensor data to identify, explain, classify, and report equipment or product defects.

## MVP Goal

Upload one industrial defect image, one inspection standard document, and an optional sensor CSV. The system automatically:

1. Identifies and describes the defect
2. Retrieves relevant inspection standards
3. Determines the severity level
4. Provides risk explanation and recommended action
5. Generates a structured Inspection Report
6. Flags whether human review is required

## MVP Scope

Included:
- Image upload
- Inspection standard document parsing
- RAG-based retrieval of standard evidence
- Defect description and simplified localization
- Agent-based decision making
- Structured report generation
- Frontend result display

Not included yet:
- Real-time video streaming
- Large-scale model training
- Multi-sensor time-series fusion
- Enterprise permission system
- Automated work order system
- Edge device deployment

## Recommended Tech Stack

Backend: Python, FastAPI, LangGraph, Chroma/FAISS, PyMuPDF, Pydantic

Vision: OpenAI/Gemini/Qwen-VL/LLaVA for the MVP; YOLO + SAM for phase 2

Frontend: React / Next.js

Data: MVTec AD, DAGM, NEU surface defect, KolektorSDD

## Current Directory Layout

```text
backend/app/main.py              # FastAPI app: /health + /api/inspect, CORS
backend/app/api/inspect.py       # /api/inspect multipart endpoint
backend/app/schemas/inspection.py# Pydantic data contract (report, defect, etc.)
backend/app/rag/document_loader.py # txt/md/pdf text extraction
backend/app/rag/retriever.py     # clause chunker + lexical retriever
backend/app/vision/defect_detector.py # detector interface + heuristic impl
backend/app/vision/yolo_detector.py # Ultralytics YOLO backend (Phase 2)
backend/app/vision/qwen_detector.py # local Qwen2.5-VL backend (Phase 2)
backend/app/vision/vlm_detector.py  # OpenAI-compatible VLM backend (Phase 2)
backend/app/vision/vlm_common.py # shared VLM prompt + JSON parsing
backend/app/vision/factory.py    # env-driven backend selection + fallback
backend/app/vision/annotator.py  # bounding-box image annotation
backend/app/agents/inspection_agent.py # severity/action/human-review decision
backend/app/services/sensor_loader.py  # sensor CSV parsing + thresholds
backend/app/services/report_generator.py # assemble InspectionReport
backend/app/services/workflow.py # end-to-end orchestration
frontend/index.html              # static upload + report UI (no build step)
frontend/app.js
frontend/styles.css
data/sample_standards/           # demo inspection standard
data/sample_reports/             # example report JSON + sample sensor CSV
notebooks/
docs/
```

## Quickstart

### Quick 1-Click Launch

- **Windows:** Double-click `start.bat` (or run `./start.bat` in PowerShell)
- **macOS / Linux:** Run `chmod +x start.sh && ./start.sh`

Both scripts automatically create `.venv`, install core lightweight dependencies, and launch the unified server at `http://localhost:8000`.

### Docker Launch (Zero Local Python Setup)

```bash
# Build and run with standard Docker
docker build -t inspection-agent .
docker run -p 8000:8000 -v "${PWD}/outputs:/app/outputs" inspection-agent

# Or using Docker Compose (if compose plugin installed):
docker compose up --build
```
Open `http://localhost:8000` in your browser.

### Manual Setup

#### Windows (PowerShell)

```powershell
# 1. Create and activate virtual environment
python -m venv .venv
.venv\Scripts\Activate.ps1

# 2. Install core lightweight dependencies
pip install -r backend/requirements.txt

# 3. Start unified server (serves frontend + API on port 8000)
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
# open http://localhost:8000
```

#### macOS / Linux

```bash
# 1. Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 2. Install core lightweight dependencies
pip install -r backend/requirements.txt

# 3. Start unified server (serves frontend + API on port 8000)
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
# open http://localhost:8000
```

### Configuration & Environment

Copy `.env.example` to `.env` to customize settings without editing code:

```bash
cp .env.example .env   # macOS/Linux
copy .env.example .env # Windows
```

Key variables available:
- `HOST`: Server host (default `0.0.0.0`)
- `PORT`: Server port (default `8000`)
- `CORS_ORIGINS`: Allowed origins (default `*` for local dev; comma-separated URLs in production)
- `MAX_UPLOAD_SIZE_MB`: Max upload size limit (default `25` MB)
- `INSPECTION_DETECTOR`: Defect detector backend (`heuristic` default, `vlm`, `qwen`, or `yolo`)


Health check:

```bash
curl http://127.0.0.1:8000/health   # -> {"status":"ok"}
```

Run a full inspection:

```bash
curl -X POST http://127.0.0.1:8000/api/inspect \
  -F "image=@your_defect.png" \
  -F "standard=@data/sample_standards/pipeline_surface_defect_standard.md" \
  -F "sensor_csv=@data/sample_reports/sample_sensors.csv" \
  -F 'vision_hints={"defect_type":"crack","confidence":0.9,"length_mm":8,"load_bearing_area":true}'
```

The response is a structured `InspectionReport` (see `data/sample_reports/example_report.json`).

### Frontend

The frontend is served directly by FastAPI at `/` (`http://localhost:8000`). No separate server or build step is required.
Upload an image + standard (+ optional sensor CSV), then view the rendered report.

## Cloud Hosting

Deploy to free or cloud hosting with zero reconfiguration:

- **Render:** Push to GitHub and deploy using [`render.yaml`](render.yaml) (1-click Blueprint).
- **Railway:** Connect repository; Railway detects [`Dockerfile`](Dockerfile) and [`railway.toml`](railway.toml).
- **Fly.io:** Run `fly launch` and `fly deploy` using [`fly.toml`](fly.toml).
- **Docker VPS / Cloud VMs:** Run `docker run -p 80:8000 inspection-agent`.

Full deployment walkthroughs are in [`docs/hosting.md`](docs/hosting.md).

## How It Works

The `/api/inspect` request runs this deterministic pipeline (`services/workflow.py`):

1. **Vision** — `DefectDetector` returns a `DefectObservation` (heuristic by default; YOLO or VLM backends in Phase 2, see below).
2. **RAG** — the standard document is parsed and chunked into clauses, then relevant clauses are retrieved lexically.
3. **Sensors** — optional CSV is parsed; the latest reading per column is checked against critical thresholds.
4. **Decision** — transparent rules assign severity, recommended action, and the human-review flag.
5. **Report** — everything is assembled into an `InspectionReport` (JSON + Markdown).

Human review is triggered when confidence < 0.70, no standard clause matches, severity is high/critical, or sensor and visual evidence conflict.

## Vision Backends (Phase 2)

The vision step is pluggable behind the `DefectDetector` interface and selected via environment variables (defaults to the dependency-free heuristic):

```bash
pip install -r backend/requirements.txt -r backend/requirements-vision.txt

# Local Qwen-VL (in-process, no server)
export INSPECTION_DETECTOR=qwen
export INSPECTION_QWEN_MODEL=Qwen/Qwen2.5-VL-3B-Instruct
export INSPECTION_QWEN_DEVICE=auto   # cuda / mps / cpu

# or YOLO
export INSPECTION_DETECTOR=yolo
export INSPECTION_YOLO_MODEL=runs/defect/best.pt

# or Qwen-VL via a local OpenAI-compatible server (Ollama/vLLM)
export INSPECTION_DETECTOR=vlm
export INSPECTION_VLM_MODEL=qwen2.5vl
export INSPECTION_VLM_BASE_URL=http://localhost:11434/v1
export INSPECTION_VLM_API_KEY=ollama
```

Backends: `heuristic` (default), `yolo` (Ultralytics), `qwen` (local Qwen2.5-VL via transformers), `vlm` (OpenAI-compatible server, including Qwen on Ollama/vLLM), `auto`. If a selected backend's dependency/config is missing, the factory falls back to the heuristic detector so the service stays up. Pass `annotate=true` to `/api/inspect` to save a bounding-box image (`annotated_image_path`). Full details in `docs/phase2_vision.md`.

## Extending the MVP

- **Real vision:** subclass `DefectDetector` (VLM/YOLO/SAM), normalize labels via `vision/labels.py`, and register it in `vision/factory.py`.
- **Embedding retrieval:** swap `StandardRetriever` for a FAISS/Chroma-backed retriever with the same `retrieve()` contract.
- **LLM explanations:** layer an LLM on top of the rule-based `decide()` for ambiguous cases.

See `docs/mvp_implementation_plan.md`, `docs/system_design.md`, and `docs/phase2_vision.md` for the full design.
