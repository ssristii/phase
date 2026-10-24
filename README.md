# Phase

Cycle-aware workout and grocery planner. Browser-first prototype built with
Streamlit and Python, with an optional Express sponsor API and MongoDB.

## Stack

- Python 3.11+ and Streamlit for the browser prototype
- MongoDB for account and check-in persistence
- Node.js 18+ Express API for sponsor integrations (Gemini, Cartesia)
- React Native / Expo mobile app (deferred)

## Project layout

```
apps/web        Streamlit prototype (Python)
apps/api        Express sponsor API (Node.js)
apps/mobile     Expo app (deferred)
docs            Specs, audits, verified features, vendor docs
```

## Quick start (browser prototype)

### 1. Install Python dependencies

```
cd apps/web
pip install -r requirements.txt
```

### 2. (Optional) Configure MongoDB

Copy `apps/web/.env.example` to `apps/web/.env` and set `MONGODB_URI`.
If `MONGODB_URI` is left unset, the app uses an in-memory store for the
session. Accounts and check-ins are then lost when the app restarts, and a
warning banner is shown. This is expected for local development without a
database.

### 3. (Optional) Start the sponsor API

```
cd apps/api
copy .env.example .env   # fill GEMINI_API_KEY / CARTESIA_API_KEY
npm install
npm run dev
```

The API listens on http://127.0.0.1:4000.

### 4. Start Streamlit

```
cd c:\Users\SRIST\phase
python -m streamlit run apps/web/streamlit_app.py --server.address 127.0.0.1
```

Open http://127.0.0.1:8501.

## Demo account

With MongoDB configured:

```
cd apps/web
python demo_seed.py
```

Then sign in with demo@phase.local / DemoPass123!.

## Tests

```
cd apps/web
python -m unittest discover -s . -p "test_*.py"

cd ../api
npm test
```

## Troubleshooting

- "No MONGODB_URI set..." warning: expected when running without MongoDB.
  Data resets on restart. Set `MONGODB_URI` in `apps/web/.env` for persistence.
- Login not working after creating an account: ensure you are running the
  latest code; the in-memory store is cached per process so accounts survive
  Streamlit reruns.
- Port 8501 in use: stop the previous process or pass `--server.port`.

## Notes

- No emojis are used anywhere in the project.
- Accounts use a one-time 10-character sign-in code; lost codes cannot be
  recovered.
