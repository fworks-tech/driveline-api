# Local Development Guide — Backend + Frontend Setup

**Audience:** Developers setting up local development environment  
**Time to complete:** ~15 minutes (including npm install)  
**Last Updated:** 2026-05-20

Complete step-by-step guide to run the full Spotter ELD stack locally (backend + frontend) for development and testing.

This guide is Docker Compose-first for the backend. Use the bootstrap script below to build and start the full backend stack with one command.

---

## Architecture

```
Your Development Machine
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│  Terminal 1: Backend          Terminal 2: Frontend         │
│  ┌──────────────────────┐     ┌──────────────────────┐    │
│  │ Django 4.2           │     │ Vite Dev Server      │    │
│  │ Port: 8000           │◄────│ Port: 3000           │    │
│  │ /api/v1/plan-route/     │     │ (auto-proxy /api)    │    │
│  └──────────────────────┘     └──────────────────────┘    │
│  Calls:                       Browser                      │
│  - Nominatim API              http://localhost:3000        │
│  - OSRM API                   ↓                            │
│  - HOS Engine                 User Interface               │
│                                                             │
│  External (Internet)                                        │
│  - nominatim.openstreetmap.org  (geocoding)                │
│  - router.project-osrm.org       (routing)                 │
└─────────────────────────────────────────────────────────────┘
```

---

## Prerequisites

### System Requirements

- **Docker Desktop** or **Docker Engine + Compose plugin**
- **Node.js 18+** (only if you also want to run the frontend)
- **npm** or **yarn** (frontend package manager)
- **Git** (for cloning repos)
- **Internet connection** (for external APIs: Nominatim, OSRM)

### Verify Installation

```bash
docker --version      # Should be installed and available
docker compose version
node --version        # Should be 18+
npm --version         # Should be 9+
git --version         # Should be 2.30+
```

---

## Phase 1: Backend Setup (Django)

### Step 1.1: Clone Backend Repository

```bash
git clone https://github.com/fworks-tech/spotter-eld-logging-api.git
cd spotter-eld-logging-api
```

### Step 1.2: Bootstrap the Backend Stack

Run the PowerShell helper script from the repository root:

```powershell
.\scripts\bootstrap_backend.ps1
```

What it does:
- Creates `.env` from `.env.example` if it is missing
- Builds the backend image
- Runs Django migrations inside the Compose stack
- Starts `web`, `db`, and `redis`

If you prefer the raw compose command, run:

```bash
docker compose up --build
```

The backend will be available at `http://localhost:8000`, and the health check is at `http://localhost:8000/health/`.

### Step 1.3: Verify Backend is Running

Open in browser: **http://localhost:8000/api/docs/**

You should see:
- ✅ Swagger UI (interactive API documentation)
- ✅ Single endpoint: `POST /api/v1/plan-route/`
- ✅ Request/response schemas
- ✅ "Try it out" button to test manually

**Keep this terminal open.** Backend is running.

---

## Phase 2: Frontend Setup (React + Vite)

### Step 2.1: Clone Frontend Repository (if not already done)

Open **new terminal window** (keep backend running in Terminal 1).

```bash
git clone https://github.com/fworks-tech/spotter-eld-logging-app.git
cd spotter-eld-logging-app/frontend
```

### Step 2.2: Create Environment Configuration

```bash
cp .env.example .env.local
```

**File: `frontend/.env.local`** (verify content)

```env
VITE_API_URL=http://localhost:8000
```

**What this does:**
- `VITE_API_URL` — Tells Vite dev server to proxy `/api/*` requests to backend on port 8000
- `VITE_` prefix — Makes it available to React code as `import.meta.env.VITE_API_URL`

### Step 2.3: Install Dependencies

```bash
npm install
```

**Expected output:**
```
added 500 packages in 45s
```

**Note:** First install takes 45-60 seconds. Subsequent installs are faster.

### Step 2.4: Start Frontend Dev Server

```bash
npm run dev
```

**Expected output:**
```
VITE v6.x.x  ready in 234 ms

➜  Local:   http://localhost:3000/
➜  press h to show help
```

**Keep this terminal open.** Frontend is running.

### Step 2.5: Verify Frontend is Running

Open in browser: **http://localhost:3000/**

You should see:
- ✅ Trip planner form (4 input fields)
- ✅ "Plan Route" submit button
- ✅ No console errors (check DevTools → Console)

---

## Phase 3: End-to-End Testing

### Step 3.1: Open Both Services

**Terminal 1 (Backend):**
```
May 20, 2026 - 14:35:42 [INFO] Starting development server at http://0.0.0.0:8000/
```

**Terminal 2 (Frontend):**
```
➜  Local:   http://localhost:3000/
```

**Browser:** http://localhost:3000/ open and visible

---

## Troubleshooting

### Docker Desktop is not running

If `docker compose up --build` fails with a `dockerDesktopLinuxEngine` pipe error on Windows, start Docker Desktop first and make sure the Linux engine is active.

```bash
docker version
docker compose up --build
```

### Port conflicts

If ports `8000`, `5432`, or `6379` are already in use, stop the conflicting service or update the Compose port mappings before retrying.

### Stale containers or volumes

If the database container gets into a bad state, remove the Compose stack and its volume, then start again:

```bash
docker compose down -v
docker compose up --build
```

### Missing `.env`

If Django starts but the backend behavior is inconsistent, confirm that `.env` exists and that it still matches `.env.example`. The Compose file loads `.env` from the project root.

### Windows file sharing or WSL2 issues

If Compose cannot mount the project directory, verify that Docker Desktop has access to the `C:\Github\spotter-eld-logging-api` folder and that WSL2 integration is enabled.

### Health endpoint check

Once the backend is up, this should return `{"status": "ok"}`:

```bash
curl http://localhost:8000/health/
```

---

## Troubleshooting

### Docker Desktop is not running

If `docker compose up --build` fails with a `dockerDesktopLinuxEngine` pipe error on Windows, start Docker Desktop first and make sure the Linux engine is active.

```bash
docker version
docker compose up --build
```

### Port conflicts

If ports `8000`, `5432`, or `6379` are already in use, stop the conflicting service or update the Compose port mappings before retrying.

### Stale containers or volumes

If the database container gets into a bad state, remove the Compose stack and its volume, then start again:

```bash
docker compose down -v
docker compose up --build
```

### Missing `.env`

If Django starts but the backend behavior is inconsistent, confirm that `.env` exists and that it still matches `.env.example`. The Compose file loads `.env` from the project root.

### Windows file sharing or WSL2 issues

If Compose cannot mount the project directory, verify that Docker Desktop has access to the `C:\Github\spotter-eld-logging-api` folder and that WSL2 integration is enabled.

### Health endpoint check

Once the backend is up, this should return `{"status": "ok"}`:

```bash
curl http://localhost:8000/health/
```

### Step 3.2: Fill Trip Planning Form

In the browser at http://localhost:3000/:

| Field | Value |
|-------|-------|
| Current Location | Chicago, IL |
| Pickup Location | Indianapolis, IN |
| Dropoff Location | Dallas, TX |
| Cycle Hours Used | 30 |

### Step 3.3: Submit Request

Click **"Plan Route"** button.

**You should see:**
- ✅ Loading spinner for 2-5 seconds
- ✅ No error messages
- ✅ Route map appears with markers
- ✅ Logbook table with multi-day events
- ✅ Trip summary (850 miles, 13.5 hours, etc.)

### Step 3.4: Monitor Request Flow

**Backend Terminal 1:**
```
[20/May/2026 14:36:22] "POST /api/v1/plan-route/ HTTP/1.1" 200 5234
```

**Frontend Console (DevTools → Console):**
```
[api] POST /plan-route/ → 200 OK (2345ms)
```

**Browser Network Tab (DevTools → Network):**
- Request: `POST /api/v1/plan-route/`
- Status: `200`
- Response size: ~5 KB
- Duration: 2–5 seconds

---

## Troubleshooting

### Backend: "Address already in use: port 8000"

**Problem:** Another process is using port 8000.

**Solution A:** Kill the process
```bash
# Windows (PowerShell)
Get-Process -Id (Get-NetTCPConnection -LocalPort 8000).OwningProcess | Stop-Process

# macOS/Linux
lsof -ti :8000 | xargs kill -9
```

**Solution B:** Use different port
```bash
docker compose down
docker compose up --build
```
If you changed the host port in `docker-compose.yml`, update `frontend/.env.local` to match.

### Frontend: "CORS error: Access to XMLHttpRequest blocked"

**Problem:** Backend CORS settings don't allow frontend.

**Solution:** Check `CORS_ALLOWED_ORIGINS` in `.env`:
```env
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
```

Must include your frontend URL.

### Frontend: "Cannot POST /api/v1/plan-route/ (404 Not Found)"

**Problem:** Proxy isn't forwarding requests to backend correctly.

**Solution:** Verify `VITE_API_URL` in `frontend/.env.local`:
```env
VITE_API_URL=http://localhost:8000
```

Then restart frontend:
```bash
npm run dev
```

### Response takes 5+ seconds

**Problem:** External APIs (Nominatim, OSRM) are slow.

**Expected:** 2–5 seconds is normal. Breaking down:
- Nominatim geocoding: 1–2 sec per address × 3 = 3–6 sec
- OSRM routing: 1–2 sec per route = 2–4 sec
- HOS engine: <500 ms

**Solution:** This is expected behavior. In production, caching and circuit breakers will improve performance (v1.0.0-beta features).

### Map doesn't show / "Invalid coordinates"

**Problem:** Frontend is using wrong coordinate order.

**Solution:** Check browser console for coordinate parsing errors. The backend returns:
- `route_coordinates` as `[lon, lat]` (GeoJSON)
- `markers.lat` / `markers.lon` as normal order

See [FRONTEND_INTEGRATION.md](FRONTEND_INTEGRATION.md#️️-critical-coordinate-system-distinction) for coordinate handling.

### "No module named 'trips'" or import error

**Problem:** Virtual environment not activated or dependencies not installed.

**Solution:**
```bash
# Activate venv
venv\Scripts\activate  # Windows

# Reinstall
pip install -r requirements.txt
```

---

## Hot Module Reload (HMR)

**Frontend (Vite):**
- Changes to `src/**/*.tsx` auto-reload in browser
- No manual refresh needed
- State is preserved (forms keep their input)

**Backend (Django):**
- Changes to `*.py` auto-reload
- Queries should reload immediately
- Models or settings changes may require manual restart

---

## Running Tests Locally

### Backend Tests

```bash
# Activate venv first
venv\Scripts\activate

# Run all tests
python -m pytest trips/tests/ -v -o addopts=""

# Run specific test
python -m pytest trips/tests/test_routing.py::TestGeocoding -v -o addopts=""

# Run with coverage
python -m pytest trips/tests/ --cov=trips --cov-report=html
```

**Expected output:**
```
trips/tests/test_routing.py::TestGeocoding::test_geocode_valid_address PASSED
trips/tests/test_api_endpoint.py::TestPlanRouteAPI::test_successful_route_planning PASSED
...
===== 12 passed in 2.34s =====
```

### Frontend Tests

```bash
# Run all tests
npm test

# Run in watch mode
npm test -- --watch

# Check coverage
npm test -- --coverage
```

---

## Stopping Services

### Backend (Terminal 1)

Press **CTRL+C** (or **CTRL+BREAK** on Windows)

```
Keyboard interrupt received: quitting.
```

### Frontend (Terminal 2)

Press **CTRL+C**

```
[VITE] server closed.
```

---

## Next Steps

### After Confirming Setup Works

1. **Explore the code:**
   - Frontend: `spotter-eld-logging-app/frontend/src/`
   - Backend: `spotter-eld-logging-api/trips/`

2. **Read the documentation:**
   - [Frontend Integration Guide](FRONTEND_INTEGRATION.md)
   - [API Contract](API_CONTRACT.md)
   - [Architecture](ARCHITECTURE.md)

3. **Try modifying:**
   - Change form input validation (frontend)
   - Add a console log to the HOS engine (backend)
   - See hot reload in action

4. **For actual development:**
   - Create a feature branch
   - Make changes
   - Run tests
   - Create a pull request

### Tips for Productive Development

- **Keep both terminals visible** — Use split screen or two monitors
- **Enable DevTools** — Browser DevTools (F12) is essential
- **Check console frequently** — Console logs help debug
- **Use Swagger UI** — http://localhost:8000/api/docs/ to manually test API
- **Read error messages** — They're detailed and helpful

---

## Verification Checklist

Use this to confirm everything is working:

- [ ] Backend running on `http://localhost:8000`
- [ ] Frontend running on `http://localhost:3000`
- [ ] Can see Swagger UI at `http://localhost:8000/api/docs/`
- [ ] Can see trip form at `http://localhost:3000`
- [ ] Submit trip with Chicago → Indianapolis → Dallas
- [ ] Response appears in 2–5 seconds
- [ ] Route map displays with markers
- [ ] Logbook shows 2 days of events
- [ ] Trip summary shows 850 miles, 13.5 hours
- [ ] No CORS errors in browser console
- [ ] No errors in backend terminal

**All checked?** ✅ You're ready to develop!

---

## Additional Commands

```bash
npm run build                      # Build for production
npm run preview                    # Preview production build
```

---

## Related Documentation

- [Frontend Integration Guide](FRONTEND_INTEGRATION.md) — API contract and integration patterns
- [API Contract](API_CONTRACT.md) — Request/response schemas
- [Architecture](ARCHITECTURE.md) — System design
- [OpenAPI Spec](openapi.yaml) — Machine-readable schema
