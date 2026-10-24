from dataclasses import dataclass
from datetime import date


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
) -> CyclePrediction:
    if unsure:
        return CyclePrediction(
            phase=None,
            confidence=None,
            reason=(
                "You marked cycle dates as unsure, so guidance uses reported "
                "symptoms only and makes no phase claim."
            ),
            cycle_day=None,
            fertile_window=None,
            population_default=False,
        )
    if last_period_start is None:
        raise ValueError("Enter a last period start date or choose unsure.")
    if last_period_start > today:
        raise ValueError("Last period start cannot be in the future.")
    if cycle_length is not None and not 21 <= cycle_length <= 35:
        raise ValueError("Cycle length must be between 21 and 35 days.")

    population_default = cycle_length is None
    length = cycle_length or 28
    cycle_day = (today - last_period_start).days % length + 1
    if cycle_day <= 5:
        phase = "Menstrual"
    elif cycle_day <= 13:
        phase = "Follicular"
    elif cycle_day <= 16:
        phase = "Ovulatory"
    else:
        phase = "Luteal"

    confidence = 0.3 if population_default else 0.45
    basis = "a population-default 28-day cycle" if population_default else "your reported start date and cycle length"
    reason = (
        f"{phase} is a low-confidence estimate based on {basis}; "
        "logged symptoms take priority."
    )
    ovulation_day = length - 14
    fertile_window = (max(1, ovulation_day - 5), min(length, ovulation_day + 1))
    return CyclePrediction(
        phase=phase,
        confidence=confidence,
        reason=reason,
        cycle_day=cycle_day,
        fertile_window=fertile_window,
        population_default=population_default,
    )


def evaluate_safety(
    today: date,
    last_period_start: date | None,
    flow: str,
    pain: int,
    severe_pain: bool,
    persistently_irregular_cycles: bool,
    positive_pregnancy_test: bool,
) -> SafetyResult:
    alerts: list[str] = []
    if last_period_start and (today - last_period_start).days >= 90:
        alerts.append("No period has been reported for 90 or more days.")
    if flow == "Very heavy":
        alerts.append("Very heavy bleeding was reported.")
    if severe_pain or pain >= 8:
        alerts.append("Severe pain was reported.")
    if persistently_irregular_cycles:
        alerts.append("Persistently short or long cycles were reported.")
    if positive_pregnancy_test:
        alerts.append("A positive pregnancy test was reported.")
    return SafetyResult(tuple(alerts))


def build_plan(
    phase: str | None,
    goal: str,
    exercises: list[str],
    energy: int,
    sleep_hours: float,
    pain: int,
) -> dict[str, str | int]:
    intensity = 2
    if phase == "Follicular":
        intensity = 3
    elif phase == "Ovulatory":
        intensity = 3
    elif phase == "Luteal":
        intensity = 2

    adjusted = False
    if (sleep_hours < 6 and pain >= 6) or energy <= 2 or pain >= 8:
        intensity = max(1, intensity - 1)
        adjusted = True

    effort = ("gentle", "moderate", "challenging")[intensity - 1]
    exercise = exercises[0] if exercises else "Bodyweight strength"
    focus = {
        "Strength": "strength practice",
        "General fitness": "balanced movement",
        "Energy": "steady, manageable movement",
    }.get(goal, "comfortable movement")

    if adjusted:
        reason = (
            f"Reduced to {effort} effort because your check-in reports "
            f"{sleep_hours:g} hours of sleep, pain {pain}/10, and energy {energy}/5."
        )
    elif phase:
        reason = (
            f"{phase} is a low-confidence starting prior for {focus}; "
            "today's reported state takes priority."
        )
    else:
        reason = (
            f"Cycle dates are unsure, so this {focus} session uses symptom-based "
            "guidance without a phase claim."
        )

    return {
        "title": f"{effort.title()} {focus}",
        "exercise": exercise,
        "sets": 2 if intensity == 1 else 3,
        "reps": "6 to 8 controlled reps" if intensity == 1 else "8 to 10 comfortable reps",
        "reason": reason,
        "confidence": "Low; a starting prior, not a prediction of ability.",
        "adjusted": int(adjusted),
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
    exercises: list[str],
    energy: int,
    sleep_hours: float,
    pain: int,
    today: date,
) -> list[dict[str, object]]:
    weekly_template = (
        ("Monday", "Strength A", "workout"),
        ("Tuesday", "Easy movement", "recovery"),
        ("Wednesday", "Strength B", "workout"),
        ("Thursday", "Rest and mobility", "rest"),
        ("Friday", "Strength C", "workout"),
        ("Saturday", "Easy cardio", "recovery"),
        ("Sunday", "Rest", "rest"),
    )
    goal_exercises = {
        "Strength": ("Goblet squat", "Dumbbell row", "Glute bridge"),
        "General fitness": ("Bodyweight squat", "Incline push-up", "Glute bridge"),
        "Energy": ("Bodyweight squat", "Glute bridge", "Calf raise"),
    }.get(goal, ("Bodyweight squat", "Glute bridge", "Walking"))
    strength_pool = list(
        dict.fromkeys(
            [name for name in exercises if name not in RECOVERY_EXERCISES]
            + list(goal_exercises)
        )
    )
    recovery_pool = [
        name for name in exercises if name in RECOVERY_EXERCISES
    ] or ["Walking", "Mobility flow"]
    schedule: list[dict[str, object]] = []
    strength_count = 0
    recovery_count = 0

    for weekday, title, day_type in weekly_template:
        item: dict[str, object] = {
            "day": weekday,
            "title": title,
            "type": day_type,
            "is_today": weekday == today.strftime("%A"),
        }
        if day_type == "rest":
            item.update(
                {
                    "exercises": [],
                    "sets": 0,
                    "reps": "Rest, or choose gentle mobility if comfortable.",
                    "reason": "A planned recovery day; adjust to how you feel.",
                }
            )
        else:
            if day_type == "workout":
                day_exercises = [
                    strength_pool[(strength_count * 2 + offset) % len(strength_pool)]
                    for offset in range(3)
                ]
                strength_count += 1
            else:
                day_exercises = [
                    recovery_pool[recovery_count % len(recovery_pool)]
                ]
                recovery_count += 1
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
            )
            item.update(
                {
                    "title": (
                        plan["title"] if item["is_today"] else title
                    ),
                    "exercises": day_exercises,
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


def grocery_sections(
    phase: str | None,
    dietary_preference: str = "No preference",
) -> dict[str, list[str]]:
    phase_produce = {
        "Menstrual": ["Spinach", "Oranges", "Carrots", "Apples"],
        "Follicular": ["Bell peppers", "Berries", "Cucumber", "Lemons"],
        "Ovulatory": ["Tomatoes", "Cucumber", "Grapes", "Avocado"],
        "Luteal": ["Sweet potatoes", "Bananas", "Broccoli", "Pears"],
        None: ["Leafy greens", "Seasonal fruit", "Carrots", "Cucumbers"],
    }[phase]
    grains = [
        "Oats",
        "Brown rice",
        "Quinoa",
        "Whole-grain bread",
    ]
    if dietary_preference == "Gluten-free":
        grains = [
            "Certified gluten-free oats",
            "Brown rice",
            "Quinoa",
            "Gluten-free bread",
        ]
    return {
        "Produce": phase_produce,
        "Protein": [
            "Lentils",
            "Chickpeas",
            "Black beans",
            "Tofu",
            "Edamame",
        ],
        "Grains and starches": grains,
        "Pantry": [
            "Pumpkin seeds",
            "Peanut butter",
            "Olive oil",
            "Canned tomatoes",
        ],
        "Flavor and extras": [
            "Garlic",
            "Onions",
            "Ginger",
            "Hummus",
        ],
    }


def grocery_list(phase: str | None, dietary_preference: str) -> list[str]:
    if dietary_preference not in {
        "No preference",
        "Vegetarian",
        "Vegan",
        "Gluten-free",
    }:
        raise ValueError("Choose a supported dietary preference.")
    return [
        item
        for section in grocery_sections(phase, dietary_preference).values()
        for item in section
    ]
