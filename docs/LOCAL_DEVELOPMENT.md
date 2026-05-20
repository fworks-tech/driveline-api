# Local Development Guide — Backend + Frontend Setup

**Audience:** Developers setting up local development environment  
**Time to complete:** ~15 minutes (including npm install)  
**Last Updated:** 2026-05-20

Complete step-by-step guide to run the full Spotter ELD stack locally (backend + frontend) for development and testing.

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
│  │ /api/plan-route/     │     │ (auto-proxy /api)    │    │
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

- **Python 3.11+** (for Django backend)
- **Node.js 18+** (for React frontend)
- **npm** or **yarn** (package manager)
- **Git** (for cloning repos)
- **Internet connection** (for external APIs: Nominatim, OSRM)

### Verify Installation

```bash
python --version      # Should be 3.11+
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

### Step 1.2: Create Python Virtual Environment

```bash
# Create venv
python -m venv venv

# Activate venv (Windows)
venv\Scripts\activate

# Activate venv (macOS/Linux)
source venv/bin/activate
```

**Expected output:** Your prompt should now show `(venv)` prefix.

### Step 1.3: Install Dependencies

```bash
pip install -r requirements.txt
```

**Expected output:**
```
Successfully installed django-4.2.13 djangorestframework-3.15.1 ... [N packages]
```

### Step 1.4: Configure Environment

Create `.env` file in project root (copy from `.env.example`):

```bash
cp .env.example .env
```

**File: `.env`** (verify these settings)

```env
DEBUG=True
DJANGO_SECRET_KEY=dev-secret-key-change-in-production
DATABASE_URL=sqlite:///db.sqlite3
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
LOG_LEVEL=INFO
```

**Key settings:**
- `DEBUG=True` — Shows detailed errors in browser
- `CORS_ALLOWED_ORIGINS=http://localhost:3000` — Allows frontend to make requests
- `DATABASE_URL=sqlite:///` — Uses local SQLite (no PostgreSQL needed)

### Step 1.5: Run Migrations (Optional)

```bash
python manage.py migrate
```

**Expected output:**
```
Operations to perform:
  Apply all migrations: auth, contenttypes, sessions
Running migrations:
  Applying contenttypes.0001_initial... OK
  Applying auth.0001_initial... OK
  ...
```

**Note:** No custom models exist in alpha, so this just sets up Django's built-in tables.

### Step 1.6: Start Backend Server

```bash
python manage.py runserver 0.0.0.0:8000
```

**Expected output:**
```
Watching for file changes with StatReloader
Performing system checks...
System check identified no issues (0 silenced).
May 20, 2026 - 14:35:42 [INFO] Starting development server at http://0.0.0.0:8000/
May 20, 2026 - 14:35:42 [INFO] Quit the server with CTRL+BREAK.
```

### Step 1.7: Verify Backend is Running

Open in browser: **http://localhost:8000/api/docs/**

You should see:
- ✅ Swagger UI (interactive API documentation)
- ✅ Single endpoint: `POST /api/plan-route/`
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
[20/May/2026 14:36:22] "POST /api/plan-route/ HTTP/1.1" 200 5234
```

**Frontend Console (DevTools → Console):**
```
[api] POST /plan-route/ → 200 OK (2345ms)
```

**Browser Network Tab (DevTools → Network):**
- Request: `POST /api/plan-route/`
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
python manage.py runserver 8001
```
Then update `.env.local` in frontend:
```env
VITE_API_URL=http://localhost:8001
```

### Frontend: "CORS error: Access to XMLHttpRequest blocked"

**Problem:** Backend CORS settings don't allow frontend.

**Solution:** Check `CORS_ALLOWED_ORIGINS` in `.env`:
```env
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
```

Must include your frontend URL.

### Frontend: "Cannot POST /api/plan-route/ (404 Not Found)"

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

## Common Commands Reference

```bash
# Backend
cd spotter-eld-logging-api
venv\Scripts\activate              # Activate virtual environment
python manage.py runserver         # Start dev server
python manage.py migrate           # Run migrations
python -m pytest trips/tests/ -v   # Run tests

# Frontend
cd spotter-eld-logging-app/frontend
npm install                        # Install dependencies
npm run dev                        # Start dev server
npm test                           # Run tests
npm run build                      # Build for production
npm run preview                    # Preview production build
```

---

## Related Documentation

- [Frontend Integration Guide](FRONTEND_INTEGRATION.md) — API contract and integration patterns
- [API Contract](API_CONTRACT.md) — Request/response schemas
- [Architecture](ARCHITECTURE.md) — System design
- [OpenAPI Spec](openapi.yaml) — Machine-readable schema
