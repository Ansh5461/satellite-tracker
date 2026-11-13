# GP Visualiser — LEO Orbital Telemetry & RF Pass Predictor

Full-stack mission-control style app for **weather LEO** and **ISS** satellites: live CelesTrak GP/TLE ingestion, **SGP4** propagation, TEME→ECEF ground tracks, ground-station pass prediction (Az/El), and **classical Doppler** curves.

## Stack

| Layer | Tech |
|-------|------|
| Backend | Python 3.11+, FastAPI, `sgp4`, NumPy, httpx, Pydantic v2 |
| Frontend | SvelteKit, Tailwind CSS, Chart.js, HTML5 Canvas map |
| Deploy | Docker + docker-compose |

## Quick start (local)

### Backend

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
PYTHONPATH=. uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:5173](http://localhost:5173) — Vite proxies `/api` and `/ws` to port 8000.

### Tests

```bash
cd backend && source .venv/bin/activate
PYTHONPATH=. pytest tests/ -q
```

### Docker

```bash
docker compose up --build
```

- API: [http://localhost:8000/docs](http://localhost:8000/docs)  
- UI: [http://localhost:3000](http://localhost:3000) (`PUBLIC_API_URL=http://localhost:8000` for browser calls)

## API

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/satellites` | Tracked sats + live sub-satellite point |
| `GET` | `/api/satellite/{norad_id}/track` | ±15 min / +95 min ground track @ 30 s |
| `POST` | `/api/passes` | 24 h passes ≥10°, Doppler curve for next pass |
| `WS` | `/ws/telemetry/{norad_id}?lat&lon&alt_m&freq_mhz` | 1 Hz live telemetry |

## Math reference

### TEME → ECEF

SGP4 outputs position \(\mathbf r_\mathrm{TEME}\). Earth rotation uses GMST \(\theta_\mathrm{GMST}\):

\[
\mathbf r_\mathrm{ECEF} = R_3(\theta_\mathrm{GMST})\,\mathbf r_\mathrm{TEME}
\]

\[
\mathbf v_\mathrm{ECEF} = R_3(\theta_\mathrm{GMST})\,\mathbf v_\mathrm{TEME} + \boldsymbol\omega_\oplus \times \mathbf r_\mathrm{ECEF}
\]

with \(\boldsymbol\omega_\oplus = [0,0,7.292115\times10^{-5}]^\top\) rad/s.

Geodetic \((\phi,\lambda,h)\) uses WGS-84 iterative latitude on ECEF.

### Topocentric look angles

Observer ECEF \(\mathbf r_\mathrm{obs}\), range \(\boldsymbol\rho = \mathbf r_\mathrm{sat}-\mathbf r_\mathrm{obs}\). Rotate to ENU:

\[
\begin{bmatrix}e\\n\\u\end{bmatrix} = T(\phi,\lambda)\,\boldsymbol\rho
\]

\[
\mathrm{Az} = \mathrm{atan2}(e,n),\quad \mathrm{El} = \mathrm{atan2}\left(u,\sqrt{e^2+n^2}\right)
\]

### Doppler (range rate)

\[
\dot\rho = \hat{\boldsymbol\rho}\cdot(\mathbf v_\mathrm{sat}-\mathbf v_\mathrm{obs}),\qquad
\Delta f = -f_0 \frac{\dot\rho}{c}
\]

Ground station \(\mathbf v_\mathrm{obs}\approx 0\). Rx frequency \(f_\mathrm{rx} = f_0 + \Delta f\).

## Data sources

- CelesTrak GP TLE: `weather` + `stations` groups (2 h in-memory TTL + `backend/data/tle_fallback.json`).

## Project layout

```
backend/
  main.py
  services/{tle_fetcher,propagator,pass_predictor}.py
  models/schemas.py
  tests/
frontend/
  src/routes/+page.svelte
  src/lib/components/
```
