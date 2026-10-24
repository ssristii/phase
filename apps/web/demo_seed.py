"""Seed a demo account with synthetic check-in history.

Run with: python demo_seed.py  (requires MONGODB_URI)
"""

from __future__ import annotations

import os
import random
from datetime import date, timedelta

from models import PROFILE_VERSION
from persistence import connect_database, create_account, save_checkin

DEMO_EMAIL = "demo@phase.local"
DEMO_PASSWORD = "DemoPass123!"


def main():
    mongo_uri = os.getenv("MONGODB_URI", "").strip()
    if not mongo_uri:
        raise SystemExit("Set MONGODB_URI before seeding.")
    database = connect_database(
        mongo_uri, (os.getenv("MONGODB_DATABASE") or "phase").strip() or "phase"
    )
    try:
        account = create_account(
            database.accounts,
            DEMO_EMAIL,
            DEMO_PASSWORD,
            profile={
                "version": PROFILE_VERSION,
                "age": 28,
                "goal": "General health",
                "workouts_per_week": 3,
                "usual_split": "Full body",
                "cycle_length": 28,
                "period_length": 5,
                "last_period_start": (date.today() - timedelta(days=12)).isoformat(),
                "symptom_mode": False,
                "readiness_weights": {"sleep": 1.0, "energy": 1.0, "pain": 1.0},
            },
        )
    except ValueError:
        raise SystemExit("Demo account already exists.")
    random.seed(7)
    today = date.today()
    for offset in range(90):
        day = today - timedelta(days=offset)
        save_checkin(
            database.checkins,
            account["_id"],
            day,
            {
                "flow": random.choice(["Light", "Medium", "None"]),
                "mood": random.choice(["Okay", "Good", "Tired"]),
                "energy": random.randint(2, 5),
                "sleep_hours": round(random.uniform(6.0, 8.5), 1),
                "pain": random.randint(0, 4),
                "workout_done": random.choice([True, False]),
                "severe_pain": False,
                "persistently_irregular_cycles": False,
                "positive_pregnancy_test": False,
            },
        )
    print("Seeded demo account:", DEMO_EMAIL, DEMO_PASSWORD)


if __name__ == "__main__":
    main()
