import hashlib
import hmac
import os
import random
import secrets
from datetime import date, datetime, timedelta, timezone
from uuid import uuid4


CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
CODE_LENGTH = 10
HASH_ITERATIONS = 200_000
DEMO_LOGIN_CODE = "1234567890"
PROFILE_VERSION = 2
PROFILE_GOALS = {
    "Strength",
    "Muscle",
    "Endurance",
    "General fitness",
    "Energy",
}
PROFILE_SPLITS = {
    "Full body",
    "Upper/Lower",
    "Push/Pull/Legs",
    "Body-part split",
    "Not sure",
}
PROFILE_CYCLE_MODES = {"period_date", "unsure", "hormonal_contraception"}


def is_demo_mode() -> bool:
    value = os.getenv("DEMO_MODE", "").strip().lower()
    return value in {"1", "true", "yes", "on"}


def is_production_mode() -> bool:
    if os.getenv("PRODUCTION", "").strip().lower() in {"1", "true", "yes", "on"}:
        return True
    return os.getenv("ENVIRONMENT", "").strip().lower() == "production"


def demo_mode_conflicts_with_production() -> bool:
    return is_demo_mode() and is_production_mode()


def normalize_login_code(code: str) -> str:
    return "".join(code.upper().replace("-", "").split())


def hash_login_code(code: str, salt: str) -> str:
    normalized = normalize_login_code(code)
    if normalized != DEMO_LOGIN_CODE:
        if len(normalized) != CODE_LENGTH or any(
            character not in CODE_ALPHABET for character in normalized
        ):
            raise ValueError("Enter the 10-character code exactly as it was shown.")
    return hashlib.pbkdf2_hmac(
        "sha256",
        normalized.encode("ascii"),
        bytes.fromhex(salt),
        HASH_ITERATIONS,
    ).hex()


def generate_login_code() -> str:
    return "".join(secrets.choice(CODE_ALPHABET) for _ in range(CODE_LENGTH))


def create_account(accounts, age: int) -> tuple[str, str]:
    if age < 18:
        raise ValueError("Phase is for adults 18 and older.")

    account_id = str(uuid4())
    code = generate_login_code()
    salt = secrets.token_hex(16)
    accounts.insert_one(
        {
            "_id": account_id,
            "login_code_salt": salt,
            "login_code_hash": hash_login_code(code, salt),
            "age": age,
            "profile": None,
            "created_at": datetime.now(timezone.utc),
        }
    )
    return account_id, code


def authenticate_account(accounts, code: str):
    normalized = normalize_login_code(code)
    if normalized == DEMO_LOGIN_CODE:
        if not is_demo_mode():
            raise ValueError("Enter the 10-character code exactly as it was shown.")
    elif len(normalized) != CODE_LENGTH or any(
        character not in CODE_ALPHABET for character in normalized
    ):
        raise ValueError("Enter the 10-character code exactly as it was shown.")
    for candidate in accounts.find(
        {},
        {
            "login_code_salt": 1,
            "login_code_hash": 1,
        },
    ):
        calculated_hash = hash_login_code(
            normalized,
            candidate["login_code_salt"],
        )
        if hmac.compare_digest(calculated_hash, candidate["login_code_hash"]):
            return accounts.find_one({"_id": candidate["_id"]})
    return None


def save_checkin(checkins, account_id: str, values: dict, checkin_date: date) -> None:
    record = {
        "account_id": account_id,
        "checkin_date": checkin_date.isoformat(),
        "flow": values["flow"],
        "mood": values["mood"],
        "energy": int(values["energy"]),
        "sleep_hours": float(values["sleep_hours"]),
        "pain": int(values["pain"]),
        "workout_done": bool(values["workout_done"]),
        "severe_pain": bool(values["severe_pain"]),
        "persistently_irregular_cycles": bool(values["irregular"]),
        "positive_pregnancy_test": bool(values["pregnancy"]),
        "cravings": values.get("cravings"),
        "updated_at": datetime.now(timezone.utc),
    }
    checkins.replace_one(
        {"account_id": account_id, "checkin_date": record["checkin_date"]},
        record,
        upsert=True,
    )


def get_checkin(checkins, account_id: str, checkin_date: date):
    return checkins.find_one(
        {
            "account_id": account_id,
            "checkin_date": checkin_date.isoformat(),
        }
    )


def list_checkins(checkins, account_id: str) -> list[dict]:
    rows = list(checkins.find({"account_id": account_id}))
    return sorted(rows, key=lambda item: item.get("checkin_date", ""))


def get_readiness_weights(model_weights, account_id: str) -> list[float] | None:
    record = model_weights.find_one(
        {"account_id": account_id, "model": "m2_readiness"}
    )
    if not record:
        return None
    weights = record.get("weights")
    if not isinstance(weights, list) or len(weights) != 9:
        return None
    return [float(value) for value in weights]


def save_readiness_weights(
    model_weights,
    account_id: str,
    weights: list[float],
    *,
    version: int = 1,
) -> None:
    model_weights.replace_one(
        {"account_id": account_id, "model": "m2_readiness"},
        {
            "account_id": account_id,
            "model": "m2_readiness",
            "version": version,
            "weights": [float(value) for value in weights],
            "updated_at": datetime.now(timezone.utc),
        },
        upsert=True,
    )


def reset_readiness_weights(model_weights, account_id: str) -> None:
    model_weights.delete_one(
        {"account_id": account_id, "model": "m2_readiness"}
    )


def add_phase_heart(
    hearts,
    account_id: str,
    phase: str,
) -> None:
    if phase not in {"Menstrual", "Follicular", "Ovulatory", "Luteal"}:
        raise ValueError("A phase estimate is required to heart a phase-keyed plan.")
    hearts.update_one(
        {
            "account_id": account_id,
            "phase": phase,
        },
        {"$setOnInsert": {"created_at": datetime.now(timezone.utc)}},
        upsert=True,
    )


def count_phase_hearts(hearts, account_id: str) -> int:
    return len(
        hearts.distinct(
            "phase",
            {"account_id": account_id},
        )
    )


def save_phase_workout_plan(
    locks,
    account_id: str,
    phase: str,
    workout_plan: list[dict],
) -> None:
    if phase not in {"Menstrual", "Follicular", "Ovulatory", "Luteal"}:
        raise ValueError("A phase estimate is required to save a phase-keyed plan.")
    locks.update_one(
        {"account_id": account_id, "phase": phase},
        {
            "$set": {
                "workout_plan": workout_plan,
                "plan_saved_at": datetime.now(timezone.utc),
            },
            "$setOnInsert": {"locked_at": None},
        },
        upsert=True,
    )


def get_phase_lock(locks, account_id: str, phase: str):
    return locks.find_one(
        {"account_id": account_id, "phase": phase, "is_locked": True}
    )


def lock_phase_plan(locks, account_id: str) -> None:
    locks.update_many(
        {"account_id": account_id},
        {
            "$set": {
                "is_locked": True,
                "locked_at": datetime.now(timezone.utc),
            }
        },
    )


def stored_profile(profile: dict) -> dict:
    cycle_mode = profile["cycle_tracking_mode"]
    goal = profile["goal"]
    usual_split = profile["usual_split"]
    workouts_per_week = int(profile["workouts_per_week"])
    last_period = profile.get("last_period")
    if cycle_mode not in PROFILE_CYCLE_MODES:
        raise ValueError("Choose a supported cycle tracking option.")
    if goal not in PROFILE_GOALS:
        raise ValueError("Choose a supported workout goal.")
    if usual_split not in PROFILE_SPLITS:
        raise ValueError("Choose a supported workout split.")
    if workouts_per_week not in range(1, 8):
        raise ValueError("Choose between one and seven workouts per week.")
    if cycle_mode == "period_date" and not isinstance(last_period, date):
        raise ValueError("A last period start date is required for cycle estimates.")

    return {
        "version": PROFILE_VERSION,
        "cycle_tracking_mode": cycle_mode,
        "cycle_date_unsure": cycle_mode != "period_date",
        "last_period_start": (
            last_period.isoformat()
            if cycle_mode == "period_date"
            else None
        ),
        "cycle_length": None,
        "goal": goal,
        "workouts_per_week": workouts_per_week,
        "usual_split": usual_split,
    }
def _clear_demo_data(database, account_id: str) -> None:
    for collection in (
        database.checkins,
        database.phase_hearts,
        database.phase_locks,
        database.model_weights,
    ):
        for document in list(collection.find({"account_id": account_id})):
            collection.delete_one({"_id": document["_id"]})


def _seed_demo_data(database, account_id: str, *, seed: int = 42, today: date | None = None) -> None:
    from models import (
        default_readiness_weights,
        encode_readiness_features,
        update_readiness_weights,
    )

    today = today or date.today()
    rng = random.Random(seed)
    _clear_demo_data(database, account_id)

    last_period = today - timedelta(days=23)
    profile = {
        "version": PROFILE_VERSION,
        "age": 27,
        "goal": "Strength",
        "workouts_per_week": 4,
        "usual_split": "Upper/Lower",
        "cycle_tracking_mode": "period_date",
        "cycle_date_unsure": False,
        "last_period_start": last_period.isoformat(),
        "cycle_length": None,
    }
    database.accounts.update_one(
        {"_id": account_id},
        {
            "$set": {
                "profile": profile,
                "age": 27,
                "demo_account": True,
                "is_demo": True,
                "demo": True,
            }
        },
    )

    moods = ["Low", "Okay", "Good", "Anxious", "Irritable", "Flat"]
    for offset in range(90):
        day = today - timedelta(days=offset)
        if offset != 0 and rng.random() < 0.12:
            continue
        cycle_day = (day - last_period).days + 1
        normalized_day = ((cycle_day - 1) % 28) + 1
        if normalized_day <= 5:
            flow = rng.choice(["Light", "Medium", "Heavy"])
        elif rng.random() < 0.15:
            flow = "Spotting"
        else:
            flow = "None"
        if normalized_day <= 5:
            pain = rng.randint(3, 7)
        elif normalized_day >= 22:
            pain = rng.randint(2, 6)
        else:
            pain = rng.randint(0, 4)
        energy = rng.randint(2, 5)
        if normalized_day >= 20:
            energy = max(1, energy - 1)
        sleep = round(rng.uniform(6.0, 8.5), 1)
        mood = rng.choice(moods)
        workout_done = rng.random() < 0.55
        cravings = None
        if offset == 0:
            flow = "None"
            mood = "Flat"
            energy = 2
            sleep = 5.0
            pain = 7
            cravings = "salty"
            workout_done = False
        values = {
            "flow": flow,
            "mood": mood,
            "energy": energy,
            "sleep_hours": sleep,
            "pain": pain,
            "workout_done": workout_done,
            "severe_pain": False,
            "irregular": False,
            "pregnancy": False,
            "cravings": cravings,
        }
        save_checkin(database.checkins, account_id, values, day)

    # Remove any three-day heavy-flow streaks from the seeded history.
    history = sorted(
        list_checkins(database.checkins, account_id),
        key=lambda item: item.get("checkin_date", ""),
    )
    heavy_streak = 0
    for row in history:
        if row.get("flow") in {"Heavy", "Very heavy"}:
            heavy_streak += 1
            if heavy_streak >= 3:
                row["flow"] = "Medium"
                save_checkin(
                    database.checkins,
                    account_id,
                    {
                        "flow": row["flow"],
                        "mood": row["mood"],
                        "energy": row["energy"],
                        "sleep_hours": row["sleep_hours"],
                        "pain": row["pain"],
                        "workout_done": row["workout_done"],
                        "severe_pain": row["severe_pain"],
                        "irregular": row["persistently_irregular_cycles"],
                        "pregnancy": row["positive_pregnancy_test"],
                        "cravings": row.get("cravings"),
                    },
                    date.fromisoformat(row["checkin_date"]),
                )
                heavy_streak = 1
        else:
            heavy_streak = 0

    for phase in ("Follicular", "Ovulatory", "Luteal"):
        add_phase_heart(database.phase_hearts, account_id, phase)

    weights = default_readiness_weights()
    history = sorted(
        list_checkins(database.checkins, account_id),
        key=lambda item: item.get("checkin_date", ""),
    )
    for row in history:
        row_date = date.fromisoformat(row["checkin_date"])
        normalized_day = ((row_date - last_period).days % 28) + 1
        if normalized_day <= 5:
            phase = "Menstrual"
        elif normalized_day < 13:
            phase = "Follicular"
        elif normalized_day <= 16:
            phase = "Ovulatory"
        else:
            phase = "Luteal"
        features = encode_readiness_features(
            sleep_hours=row["sleep_hours"],
            energy=row["energy"],
            pain=row["pain"],
            mood=row["mood"],
            phase=phase,
        )
        label_too_much = row["energy"] <= 2 and row["pain"] >= 6
        weights = update_readiness_weights(
            weights, features, label_too_much=label_too_much
        )
    save_readiness_weights(database.model_weights, account_id, weights, version=1)

    database.accounts.update_one(
        {"_id": account_id},
        {
            "$set": {
                "session_ratings": [
                    rng.randint(1, 5) for _ in range(rng.randint(10, 14))
                ]
            }
        },
    )


def ensure_demo_account(database, *, seed: int = 42, today: date | None = None, reset: bool = False):
    if not is_demo_mode():
        return None
    if demo_mode_conflicts_with_production():
        raise RuntimeError(
            "DEMO_MODE cannot be enabled with a production flag."
        )
    today = today or date.today()
    accounts = database.accounts
    existing = accounts.find_one({"demo_account": True})
    if existing is None:
        account_id = str(uuid4())
        salt = secrets.token_hex(16)
        accounts.insert_one(
            {
                "_id": account_id,
                "login_code_salt": salt,
                "login_code_hash": hash_login_code(DEMO_LOGIN_CODE, salt),
                "age": 27,
                "profile": None,
                "created_at": datetime.now(timezone.utc),
                "demo_account": True,
                "is_demo": True,
                "demo": True,
            }
        )
        existing = accounts.find_one({"_id": account_id})
    account_id = existing["_id"]
    _seed_demo_data(database, account_id, seed=seed, today=today)
    return accounts.find_one({"_id": account_id})


seed_demo_account = ensure_demo_account
create_demo_account = ensure_demo_account
reset_demo_account = ensure_demo_account
reset_demo = ensure_demo_account
demo_login_code = DEMO_LOGIN_CODE
demo_mode = is_demo_mode

