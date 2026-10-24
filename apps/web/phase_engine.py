from dataclasses import dataclass
from datetime import date


PHASES = ("Menstrual", "Follicular", "Ovulatory", "Luteal")


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


def grocery_list(phase: str | None, dietary_preference: str) -> list[str]:
    phase_items = {
        "Menstrual": ["Lentils", "Spinach", "Oats", "Oranges"],
        "Follicular": ["Chickpeas", "Bell peppers", "Brown rice", "Berries"],
        "Ovulatory": ["Tofu", "Tomatoes", "Quinoa", "Cucumber"],
        "Luteal": ["Beans", "Sweet potatoes", "Pumpkin seeds", "Bananas"],
        None: ["Beans", "Oats", "Leafy greens", "Seasonal fruit"],
    }
    items = phase_items[phase]
    if dietary_preference == "Vegetarian":
        return items
    if dietary_preference == "Vegan":
        return items
    if dietary_preference == "Gluten-free":
        return [item for item in items if item not in {"Oats", "Brown rice"}] + [
            "Potatoes"
        ]
    return items
