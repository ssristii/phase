import hashlib
import hmac
import secrets
from datetime import date, datetime, timezone
from uuid import uuid4


CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
CODE_LENGTH = 10
HASH_ITERATIONS = 200_000


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
    plan_kind: str,
    week: int,
) -> None:
    if phase not in {"Menstrual", "Follicular", "Ovulatory", "Luteal"}:
        raise ValueError("A phase estimate is required to heart a phase-keyed plan.")
    if plan_kind not in {"workout", "grocery"} or week not in range(1, 5):
        raise ValueError("Choose a plan and week from the four-week plan.")
    hearts.update_one(
        {
            "account_id": account_id,
            "phase": phase,
            "plan_kind": plan_kind,
            "week": week,
        },
        {"$setOnInsert": {"created_at": datetime.now(timezone.utc)}},
        upsert=True,
    )


def count_phase_hearts(hearts, account_id: str, phase: str) -> int:
    return hearts.count_documents({"account_id": account_id, "phase": phase})


def get_phase_lock(locks, account_id: str, phase: str):
    return locks.find_one({"account_id": account_id, "phase": phase})


def lock_phase_plan(
    locks,
    account_id: str,
    phase: str,
    workout_plan: dict,
    grocery_items: list[str],
) -> None:
    locks.update_one(
        {"account_id": account_id, "phase": phase},
        {
            "$setOnInsert": {
                "locked_at": datetime.now(timezone.utc),
                "workout_plan": workout_plan,
                "grocery_items": grocery_items,
            }
        },
        upsert=True,
    )


def stored_profile(profile: dict) -> dict:
    return {
        "cycle_date_unsure": bool(profile["unsure"]),
        "last_period_start": (
            None if profile["unsure"] else profile["last_period"].isoformat()
        ),
        "cycle_length": profile["cycle_length"],
        "goal": profile["goal"],
        "exercises": list(profile["exercises"])[:5],
        "dietary_preference": profile["diet"],
    }
