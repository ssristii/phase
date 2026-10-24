import hashlib
import hmac
import secrets
from datetime import date, datetime, timezone
from uuid import uuid4


CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
CODE_LENGTH = 10
HASH_ITERATIONS = 200_000
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


def normalize_login_code(code: str) -> str:
    return "".join(code.upper().replace("-", "").split())


def hash_login_code(code: str, salt: str) -> str:
    normalized = normalize_login_code(code)
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
    if len(normalized) != CODE_LENGTH or any(
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
