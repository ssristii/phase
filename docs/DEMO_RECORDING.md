# Demo recording pre-flight

Before recording the demo, run these steps:

1. Set `DEMO_MODE=1` and ensure no production flag is set.
2. Start MongoDB and the Streamlit app.
3. Run the Gemini warm-up script to cache provider content:

   ```bash
   cd apps/web
   python scripts/demo_warmup.py
   ```

   Re-run the warm-up on the recording day because the meal idea is cached per day.
4. Sign in with the preset demo code `1234567890`.
5. Confirm the Moonrise sequence plays and opens Today.
6. Confirm the "Synthetic demo data" chip is visible on Today and Report.
7. Test Reset demo restores the seeded state.
