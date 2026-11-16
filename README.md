# Real-Time LEO Orbital Telemetry & RF Pass Predictor

Production-oriented full-stack system for **LEO weather satellites + ISS**: CelesTrak OMM ingestion with Redis stale-while-revalidate caching, vectorized SGP4 (`SatrecArray`), TEME→ITRS transforms with polar motion, relativistic Doppler / FSPL / refraction, eclipse & conjunction screening, CubeSat attitude simulation, and a 60 FPS Three.js visualizer with Hermite dead-reckoning.

## Architecture

```
CelesTrak OMM ──httpx──► ingestion (SWR) ──► Redis
                                              │
                         ticker (1–2 Hz) ◄────┤
                              │               │
                         PUBLISH frames:* ────┤
                                              ▼s
                         FastAPI hub ──WebSocket──► SvelteKit
                              │                      │
                         ProcessPool            SceneController
                         (passes/TCA/…)         + geometry worker
```

See [docs/adr/](docs/adr/) for Architecture Decision Records and [docs/physics/](docs/physics/) for KaTeX derivations.

## Stack

| Layer | Tech |
|-------|------|
| Backend | Python 3.12, FastAPI, NumPy, SciPy, sgp4, Astropy, Redis, orjson |
| Ticker | Dedicated process publishing state vectors @ 1–2 Hz |
| Frontend | SvelteKit 5, Three.js, Chart.js, Web Workers |
| Deploy | Docker Compose (`redis`, `backend`, `ticker`, `frontend`) |

## Quick start

### Docker (recommended)

```bash
docker compose up --build
```

- API docs: http://localhost:8000/docs  
- Health: http://localhost:8000/api/v1/health  
- UI: http://localhost:3000  

### Local backend

```bash
# Redis must be running locally
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
PYTHONPATH=. uvicorn app.main:app --reload --port 8000
# separate terminal:
PYTHONPATH=. python -m app.streaming.ticker
```

### Local frontend

```bash
cd frontend
npm install
npm run dev
```

## API (v1)

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/v1/health` | Redis + ticker heartbeat + IERS status |
| `GET` | `/api/v1/catalog` | OMM catalog with B* / epoch-age |
| `GET` | `/api/v1/satellites/{id}/track` | Ground track with ITRS keyframes |
| `POST` | `/api/v1/passes` | Multi-hour passes + Doppler/FSPL curve |
| `GET` | `/api/v1/satellites/{id}/eclipses` | Umbra/penumbra events |
| `GET` | `/api/v1/conjunctions` | TCA screening alerts |
| `POST` | `/api/v1/attitude/simulate` | Torque-free CubeSat ODE |
| `WS` | `/ws/v1/telemetry?norad&lat&lon&alt_m&freq_hz` | Live frames |

## Tests & validation

```bash
cd backend && source .venv/bin/activate
PYTHONPATH=. pytest tests/ -q
# validation suite (astropy/Vallado fidelity):
PYTHONPATH=. pytest tests/validation -m validation -q
```

```bash
cd frontend && npm test
```

Reproducible notebook:

```bash
jupyter nbconvert --to notebook --execute notebooks/validation_report.ipynb
```

**Important:** position errors `< 10 m` assert *implementation fidelity* against reference SGP4/astropy transforms — not absolute orbit determination accuracy (~1 km at TLE epoch).

## Project layout

```
backend/app/{ingestion,propagation,physics,streaming,schemas}/
frontend/src/lib/{renderer,workers,net,stores,components}/
docs/{adr,physics}/
notebooks/validation_report.ipynb
data/sdr_captures/   # synthetic + hook for real SDR CSVs
```

## License / data

CelesTrak GP/OMM elements are used under CelesTrak terms. Synthetic SDR file is labelled and for demo only.
