# Running Phase in a browser

The browser prototype uses MongoDB Atlas to save accounts and daily check-ins.
It does not use names, emails, phone numbers, or passwords. New accounts get a
10-character code that is shown once. MongoDB stores the per-account salt and
PBKDF2 hash, never the readable sign-in code.

## Configure MongoDB

1. Create a MongoDB Atlas cluster and database user.
2. In Atlas Network Access, allow the current computer's public IP address.
   Avoid allowing access from every IP for a public deployment.
3. Copy the application's connection string from Atlas.
4. Copy `apps/web/.env.example` to `apps/web/.env`.
5. Set `MONGODB_URI` to the Atlas connection string and replace its username,
   password, and cluster host. Keep this file private; it is ignored by Git.

## Start the app

In one PowerShell terminal:

```powershell
Set-Location C:\Users\SRIST\phase\apps\api
npm run dev
```

This API is bound to `127.0.0.1` for local browser use. It is not exposed to
other devices on shared Wi-Fi.

In another PowerShell terminal:

```powershell
Set-Location C:\Users\SRIST\phase
python -m pip install -r apps\web\requirements.txt
python -m streamlit run apps\web\streamlit_app.py --server.address 127.0.0.1
```

Open `http://127.0.0.1:8501`. Create an account, save the code shown once,
complete profile setup, submit today's check-in, and continue to the dashboard.

## Voice check-in

Copy `apps/api/.env.example` to `apps/api/.env` and set `CARTESIA_API_KEY` and
`GEMINI_API_KEY` there. Restart the API after changing these values. The browser
records then uploads audio to Cartesia; this is not live transcription. If the
browser cannot access its microphone, use the audio-file upload or the tap form.
Review and correct the transcript before asking Gemini to suggest check-in
fields. The API keys stay in the local API environment, never in the browser app.

The MongoDB URI contains database credentials. Never paste it into chat, commit
it, or put it in client-visible settings. For a hosted deployment, use the
hosting provider's server-side secret manager and restrict database network
access; do not expose the local unauthenticated API or `MONGODB_URI`.
