# Local run (browser prototype)

## Prerequisites
- Python 3.11+ with pip packages from `apps/web/requirements.txt`
- Node.js 18+ (for the Express sponsor API)
- MongoDB connection string (optional; in-memory fallback is used when unset)

## Start the API (optional, needed for Gemini/Cartesia)
```
cd apps/api
copy .env.example .env   # then fill GEMINI_API_KEY / CARTESIA_API_KEY
npm install
npm run dev
```
API listens on http://127.0.0.1:4000.

## Start Streamlit
```
cd c:\Users\SRIST\phase
python -m streamlit run apps/web/streamlit_app.py --server.address 127.0.0.1
```
Open http://127.0.0.1:8501.

## Without MongoDB
Leave `MONGODB_URI` unset. The app uses an in-memory store; accounts and check-ins are lost on restart. A warning banner is shown.

## Demo account
With MongoDB configured:
```
cd apps/web
python demo_seed.py
```
Then sign in with demo@phase.local / DemoPass123!.

## Browser test checklist
1. Sign up with age 18+, complete profile.
2. Complete daily check-in; verify safety banner appears for severe pain.
3. Dashboard tabs: Today, Train, Meals, What might help, Report.
4. Train tab: lock plan after 4 hearts.
5. Meals tab: daily idea with ingredients and steps.
6. Report tab: stats grid and Export PDF.
7. Clear button on transcript: clears text without reloading.
8. Under-18 sign-up: polite block, nothing stored.

## Tests
```
cd apps/web
python -m unittest discover -s . -p "test_*.py"
cd ../api
npm test
```
