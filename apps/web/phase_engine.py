from dataclasses import dataclass
from datetime import date
from typing import Sequence

from models import (
    build_cycle_model,
    default_readiness_weights,
    encode_readiness_features,
    evaluate_escalation,
    phase_for_day,
    predict_readiness,
    readiness_plan_multiplier,
)


PHASES = ("Menstrual", "Follicular", "Ovulatory", "Luteal")
RECOVERY_EXERCISES = {
    "Cat-cow stretch",
    "Hip flexor stretch",
    "Hamstring stretch",
    "Walking",
    "Cycling",
    "Easy dance",
    "Mobility flow",
}
EXERCISE_CATALOG = (
    "Bodyweight squat",
    "Goblet squat",
    "Split squat",
    "Reverse lunge",
    "Step-up",
    "Glute bridge",
    "Hip hinge",
    "Romanian deadlift",
    "Calf raise",
    "Wall push-up",
    "Incline push-up",
    "Dumbbell chest press",
    "Dumbbell row",
    "Resistance-band row",
    "Overhead press",
    "Lateral raise",
    "Biceps curl",
    "Triceps extension",
    "Dead bug",
    "Bird dog",
    "Front plank",
    "Side plank",
    "Farmer carry",
    "Cat-cow stretch",
    "Hip flexor stretch",
    "Hamstring stretch",
    "Walking",
    "Cycling",
    "Easy dance",
    "Mobility flow",
)


@dataclass(frozen=True)
class CyclePrediction:
    phase: str | None
    confidence: float | None
    reason: str
    cycle_day: int | None
    fertile_window: tuple[int, int] | None
    population_default: bool
    symptom_mode: bool = False
    predicted_length: float | None = None


@dataclass(frozen=True)
class SafetyResult:
    alerts: tuple[str, ...]

    @property
    def suppress_plan(self) -> bool:
        return bool(self.alerts)


def predict_cycle(
    today: date,
    last_period_start: date | None,
    cycle_length: int | None = None,
    unsure: bool = False,
    checkins: Sequence[dict] | None = None,
    tracking_mode: str | None = None,
) -> CyclePrediction:
    """Estimate phase via M1. Confidence is never for display (always None)."""
    del cycle_length  # learned from logs; retained in signature for callers
    mode = tracking_mode
    if mode is None:
        mode = "unsure" if unsure else "period_date"
    if mode == "period_date" and last_period_start is None and not checkins:
        raise ValueError("Enter a last period start date or choose unsure.")
    if last_period_start is not None and last_period_start > today:
        raise ValueError("Last period start cannot be in the future.")

    state = build_cycle_model(
        checkins or [],
        today=today,
        tracking_mode=mode,
        last_period_start=last_period_start,
    )
    day = phase_for_day(state, today=today)
    return CyclePrediction(
        phase=day.phase,
        confidence=None,
        reason=day.message,
        cycle_day=day.cycle_day,
        fertile_window=None if state.symptom_mode else state.fertile_window,
        population_default=state.observed_cycle_count == 0,
        symptom_mode=state.symptom_mode,
        predicted_length=state.predicted_length,
    )


def evaluate_safety(
    today: date,
    last_period_start: date | None,
    flow: str,
    pain: int,
    severe_pain: bool,
    persistently_irregular_cycles: bool,
    positive_pregnancy_test: bool,
    checkins: Sequence[dict] | None = None,
    cycle_lengths: Sequence[int] | None = None,
) -> SafetyResult:
    """Fixed escalation rules. History-backed when checkins are provided."""
    history = list(checkins or [])
    if not any(
        (
            item.get("checkin_date") == today
            or item.get("checkin_date") == today.isoformat()
        )
        for item in history
    ):
        history.append(
            {
                "checkin_date": today,
                "flow": flow,
                "pain": pain,
            }
        )
    if last_period_start is not None and not any(
        is_bleeding_proxy(item) for item in history
    ):
        history.append(
            {
                "checkin_date": last_period_start,
                "flow": "Light",
                "pain": 0,
            }
        )

    alerts = list(
        evaluate_escalation(
            today=today,
            checkins=history,
            cycle_lengths=cycle_lengths or (),
            positive_pregnancy_test=positive_pregnancy_test,
        )
    )
    # Keep single-day hard signals used by the existing UI checkboxes.
    if severe_pain or pain >= 8:
        if not any("Pain of 8" in alert or "Severe pain" in alert for alert in alerts):
            alerts.append("Severe pain was reported.")
    if flow == "Very heavy" and not any("Heavy flow" in alert for alert in alerts):
        alerts.append("Very heavy bleeding was reported.")
    if persistently_irregular_cycles and not any(
        "Three of the last four" in alert for alert in alerts
    ):
        alerts.append("Persistently short or long cycles were reported.")
    return SafetyResult(tuple(alerts))


def is_bleeding_proxy(item: dict) -> bool:
    flow = item.get("flow")
    return flow in {"Light", "Moderate", "Heavy", "Very heavy", "Medium"}


def build_plan(
    phase: str | None,
    goal: str,
    exercises: list[str],
    energy: int,
    sleep_hours: float,
    pain: int,
    mood: str = "Okay",
    readiness_weights: Sequence[float] | None = None,
) -> dict[str, str | int | float]:
    weights = (
        list(readiness_weights)
        if readiness_weights is not None
        else default_readiness_weights()
    )
    features = encode_readiness_features(
        sleep_hours=sleep_hours,
        energy=energy,
        pain=pain,
        mood=mood,
        phase=phase,
    )
    readiness = predict_readiness(weights, features)
    # Hard override: pain >= 8 today forces recovery.
    tier = "recovery" if pain >= 8 else readiness.tier
    multiplier = readiness_plan_multiplier(tier)

    intensity = 2
    if phase == "Follicular":
        intensity = 3
    elif phase == "Ovulatory":
        intensity = 3
    elif phase == "Luteal":
        intensity = 2

    if tier == "recovery" or multiplier == 0.0:
        intensity = 1
        adjusted = True
        sets = 2
        reps = "easy mobility and an easy walk"
        effort = "gentle"
    elif tier == "reduce":
        intensity = max(1, intensity - 1)
        adjusted = True
        base_sets = 2 if intensity == 1 else 3
        sets = max(2, round(base_sets * 0.8))
        reps = "6 to 8 controlled reps" if intensity == 1 else "8 to 10 comfortable reps"
        effort = ("gentle", "moderate", "challenging")[intensity - 1]
    else:
        adjusted = False
        sets = 2 if intensity == 1 else 3
        reps = "6 to 8 controlled reps" if intensity == 1 else "8 to 10 comfortable reps"
        effort = ("gentle", "moderate", "challenging")[intensity - 1]

    exercise = exercises[0] if exercises else "Bodyweight strength"
    if tier == "recovery":
        exercise = "Mobility flow"
    focus = {
        "Strength": "strength practice",
        "Muscle": "muscle-building strength practice",
        "Endurance": "endurance-focused movement",
        "General fitness": "balanced movement",
        "Energy": "steady, manageable movement",
    }.get(goal, "comfortable movement")

    if tier == "recovery":
        reason = (
            f"Recovery session because readiness is low "
            f"(sleep {sleep_hours:g}h, pain {pain}/10, energy {energy}/5)."
        )
    elif adjusted:
        reason = (
            f"Reduced to {effort} effort from your logged state "
            f"(sleep {sleep_hours:g}h, pain {pain}/10, energy {energy}/5)."
        )
    elif phase:
        reason = (
            f"{phase} is a starting prior for {focus}; "
            "today's reported state takes priority."
        )
    else:
        reason = (
            f"Cycle-based adjustment is off; this {focus} session uses "
            "symptom-based guidance."
        )

    return {
        "title": f"{effort.title()} {focus}" if tier != "recovery" else "Recovery mobility",
        "exercise": exercise,
        "sets": sets,
        "reps": reps,
        "reason": reason,
        "adjusted": int(adjusted),
        "readiness": round(readiness.r_hat, 4),
        "tier": tier,
    }


def validate_exercises(raw: str) -> tuple[list[str], list[str]]:
    by_normalized_name = {
        " ".join(name.casefold().split()): name for name in EXERCISE_CATALOG
    }
    selected: list[str] = []
    unsupported: list[str] = []
    for value in raw.replace("\n", ",").split(","):
        candidate = value.strip()
        if not candidate:
            continue
        canonical = by_normalized_name.get(" ".join(candidate.casefold().split()))
        if canonical is None:
            unsupported.append(candidate)
        elif canonical not in selected:
            selected.append(canonical)
    return selected, unsupported


def weekly_workout_schedule(
    phase: str | None,
    goal: str,
    workouts_per_week: int,
    usual_split: str,
    energy: int,
    sleep_hours: float,
    pain: int,
    today: date,
    mood: str = "Okay",
    readiness_weights: Sequence[float] | None = None,
) -> list[dict[str, object]]:
    if workouts_per_week not in range(1, 8):
        raise ValueError("Workouts per week must be between 1 and 7.")
    split_templates = {
        "Full body": (
            ("Full body A", ("Goblet squat", "Dumbbell row", "Glute bridge")),
            ("Full body B", ("Romanian deadlift", "Incline push-up", "Dead bug")),
            ("Full body C", ("Split squat", "Overhead press", "Farmer carry")),
        ),
        "Upper/Lower": (
            ("Upper body", ("Dumbbell row", "Dumbbell chest press", "Lateral raise")),
            ("Lower body", ("Goblet squat", "Romanian deadlift", "Glute bridge")),
        ),
        "Push/Pull/Legs": (
            ("Push", ("Incline push-up", "Overhead press", "Triceps extension")),
            ("Pull", ("Dumbbell row", "Biceps curl", "Farmer carry")),
            ("Legs", ("Goblet squat", "Romanian deadlift", "Calf raise")),
        ),
        "Body-part split": (
            ("Chest and triceps", ("Dumbbell chest press", "Incline push-up", "Triceps extension")),
            ("Back and biceps", ("Dumbbell row", "Resistance-band row", "Biceps curl")),
            ("Legs", ("Goblet squat", "Split squat", "Calf raise")),
            ("Shoulders and core", ("Overhead press", "Lateral raise", "Dead bug")),
        ),
        "Not sure": (
            ("Full body", ("Bodyweight squat", "Dumbbell row", "Glute bridge")),
        ),
    }
    if usual_split not in split_templates:
        raise ValueError("Choose a supported workout split.")

    weekdays = (
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday",
    )
    training_days = {
        (index * len(weekdays)) // workouts_per_week
        for index in range(workouts_per_week)
    }
    split = split_templates[usual_split]
    schedule: list[dict[str, object]] = []

    for day_index, weekday in enumerate(weekdays):
        is_training_day = day_index in training_days
        title, day_exercises = split[
            sum(index in training_days for index in range(day_index)) % len(split)
        ] if is_training_day else ("Rest", ())
        item: dict[str, object] = {
            "day": weekday,
            "title": title,
            "type": "workout" if is_training_day else "rest",
            "is_today": weekday == today.strftime("%A"),
        }
        if not is_training_day:
            item.update(
                {
                    "exercises": [],
                    "sets": 0,
                    "reps": "Rest and recover.",
                    "reason": "A planned rest day between training sessions.",
                }
            )
        else:
            day_energy = energy if item["is_today"] else 3
            day_sleep = sleep_hours if item["is_today"] else 7.0
            day_pain = pain if item["is_today"] else 0
            plan = build_plan(
                phase,
                goal,
                day_exercises,
                day_energy,
                day_sleep,
                day_pain,
                mood=mood if item["is_today"] else "Okay",
                readiness_weights=readiness_weights,
            )
            item.update(
                {
                    "title": (
                        f"{title} - {plan['title']}"
                        if item["is_today"]
                        else title
                    ),
                    "exercises": list(day_exercises),
                    "sets": plan["sets"],
                    "reps": plan["reps"],
                    "reason": (
                        plan["reason"]
                        if item["is_today"]
                        else f"{phase or 'Symptom-based'} starting-prior plan; "
                        "check your energy, sleep, and pain again before this session."
                    ),
                }
            )
        schedule.append(item)
    return schedule
