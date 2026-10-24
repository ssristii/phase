"""Per-user online models for Phase.

M1: cycle-length and bleed-length Normal-Inverse-Gamma posteriors with
exponential forgetting. M2: online logistic regression for readiness.

These are small per-user Bayesian / logistic estimators. They are not
pretrained and not deep learning.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Iterable, Sequence


# --- M1 config (starting values, not clinical standards) ---
CYCLE_GAMMA = 0.92
CYCLE_MU0 = 28.0
CYCLE_KAPPA0 = 2.0
CYCLE_ALPHA0 = 2.0
CYCLE_BETA0 = 12.25
CYCLE_MIN = 15
CYCLE_MAX = 90

BLEED_MU0 = 5.0
BLEED_KAPPA0 = 2.0
BLEED_ALPHA0 = 2.0
BLEED_BETA0 = 2.25
BLEED_MIN = 2
BLEED_MAX = 8

SYMPTOM_SD_THRESHOLD = 5.0
LUTEAL_FIXED_DAYS = 14

# Flow values treated as bleeding (light or more). Spotting does not start a cycle.
BLEEDING_FLOWS = frozenset({"Light", "Moderate", "Heavy", "Very heavy", "Medium"})
NO_FLOW = frozenset({"None", "Spotting", ""})

# --- M2 config ---
M2_VERSION = 1
M2_ETA = 0.1
M2_LAMBDA = 0.5
M2_PHASE_LAMBDA = 2.0
M2_CLIP = 2.0
M2_W0 = (-1.8, -1.8, -1.5, -0.9, 0.0, 0.0, 0.0, 0.0, 3.3)
M2_PHASE_INDEX = (4, 5, 6, 7)  # menstrual, follicular, ovulatory, luteal
TIER_AS_PLANNED = 0.65
TIER_REDUCE = 0.40

PHASES = ("Menstrual", "Follicular", "Ovulatory", "Luteal")
MOOD_TO_N = {
    "Low": 0.0,
    "Anxious": 0.0,
    "Irritable": 0.25,
    "Flat": 0.25,
    "Okay": 0.5,
    "Ok": 0.5,
    "Good": 0.75,
    "Bright": 1.0,
}


@dataclass(frozen=True)
class NigPosterior:
    kappa: float
    mu: float
    alpha: float
    beta: float

    @property
    def point_estimate(self) -> float:
        return self.mu

    @property
    def predictive_scale_sq(self) -> float:
        return self.beta * (self.kappa + 1.0) / (self.alpha * self.kappa)

    @property
    def predictive_nu(self) -> float:
        return 2.0 * self.alpha

    @property
    def predictive_sd(self) -> float:
        """Population sd of the Student-t predictive (nu > 2)."""
        nu = self.predictive_nu
        if nu <= 2:
            return float("inf")
        return math.sqrt(nu / (nu - 2.0) * self.predictive_scale_sq)


@dataclass(frozen=True)
class CycleObservation:
    length: int
    valid: bool


@dataclass(frozen=True)
class CycleModelState:
    cycle_posterior: NigPosterior
    bleed_posterior: NigPosterior
    observed_cycle_count: int
    valid_cycle_lengths: tuple[int, ...]
    excluded_cycle_count: int
    last_period_start: date | None
    predicted_length: float
    predicted_bleed: float
    ovulation_day: int
    fertile_window: tuple[int, int]
    symptom_mode: bool
    reason: str


@dataclass(frozen=True)
class DayPhase:
    phase: str | None
    cycle_day: int | None
    late_estimate: bool
    message: str


@dataclass(frozen=True)
class ReadinessResult:
    r_hat: float
    p_too_much: float
    tier: str
    weights: tuple[float, ...]
    features: tuple[float, ...]


def _nig_prior(mu0: float, kappa0: float, alpha0: float, beta0: float) -> NigPosterior:
    return NigPosterior(kappa=kappa0, mu=mu0, alpha=alpha0, beta=beta0)


def fit_nig(
    observations: Sequence[float],
    *,
    mu0: float,
    kappa0: float,
    alpha0: float,
    beta0: float,
    gamma: float = CYCLE_GAMMA,
) -> NigPosterior:
    """Weighted Normal-Inverse-Gamma posterior; empty obs returns the prior."""
    if not observations:
        return _nig_prior(mu0, kappa0, alpha0, beta0)

    n = len(observations)
    weights = [gamma ** (n - 1 - i) for i in range(n)]
    total_w = sum(weights)
    mean = sum(w * value for w, value in zip(weights, observations)) / total_w
    scatter = sum(w * (value - mean) ** 2 for w, value in zip(weights, observations))

    kappa_n = kappa0 + total_w
    mu_n = (kappa0 * mu0 + total_w * mean) / kappa_n
    alpha_n = alpha0 + total_w / 2.0
    beta_n = (
        beta0
        + scatter / 2.0
        + (kappa0 * total_w * (mean - mu0) ** 2) / (2.0 * kappa_n)
    )
    return NigPosterior(kappa=kappa_n, mu=mu_n, alpha=alpha_n, beta=beta_n)


def is_bleeding(flow: str | None) -> bool:
    return (flow or "") in BLEEDING_FLOWS


def detect_period_starts(
    checkins: Sequence[dict],
) -> tuple[list[date], list[int]]:
    """Return period-start dates and bleed lengths from dated flow logs.

    A new cycle starts on a day with flow of light or more after three or more
    consecutive days without bleeding flow.
    """
    ordered = sorted(
        (
            item
            for item in checkins
            if item.get("checkin_date") and item.get("flow") is not None
        ),
        key=lambda item: item["checkin_date"],
    )
    starts: list[date] = []
    bleeds: list[int] = []
    dry_streak = 3  # allow the first bleeding day to count as a start
    bleed_run = 0

    for item in ordered:
        day = item["checkin_date"]
        if isinstance(day, str):
            day = date.fromisoformat(day)
        bleeding = is_bleeding(item.get("flow"))
        if bleeding:
            if dry_streak >= 3:
                if starts and bleed_run > 0:
                    bleeds.append(bleed_run)
                starts.append(day)
                bleed_run = 1
            else:
                bleed_run += 1
            dry_streak = 0
        else:
            dry_streak += 1
    if starts and bleed_run > 0:
        bleeds.append(bleed_run)
    return starts, bleeds


def cycle_lengths_from_starts(starts: Sequence[date]) -> list[CycleObservation]:
    lengths: list[CycleObservation] = []
    for index in range(1, len(starts)):
        length = (starts[index] - starts[index - 1]).days
        lengths.append(
            CycleObservation(
                length=length,
                valid=CYCLE_MIN <= length <= CYCLE_MAX,
            )
        )
    return lengths


def _ovulation_day(expected_length: float) -> int:
    rounded = max(1, int(round(expected_length)))
    ovulation = rounded - LUTEAL_FIXED_DAYS
    low = 8
    high = max(low, rounded - 10)
    return min(max(ovulation, low), high)


def build_cycle_model(
    checkins: Sequence[dict],
    *,
    today: date,
    tracking_mode: str = "period_date",
    last_period_start: date | None = None,
) -> CycleModelState:
    starts, bleed_runs = detect_period_starts(checkins)
    if last_period_start is not None and (
        not starts or starts[-1] != last_period_start
    ):
        # Prefer an explicit onboarding date when logs have not yet recorded it.
        if not starts or last_period_start > starts[-1]:
            starts = list(starts) + [last_period_start]

    observations = cycle_lengths_from_starts(starts)
    valid_lengths = [obs.length for obs in observations if obs.valid]
    excluded = sum(1 for obs in observations if not obs.valid)

    cycle_posterior = fit_nig(
        [float(length) for length in valid_lengths],
        mu0=CYCLE_MU0,
        kappa0=CYCLE_KAPPA0,
        alpha0=CYCLE_ALPHA0,
        beta0=CYCLE_BETA0,
        gamma=CYCLE_GAMMA,
    )
    bleed_posterior = fit_nig(
        [float(run) for run in bleed_runs],
        mu0=BLEED_MU0,
        kappa0=BLEED_KAPPA0,
        alpha0=BLEED_ALPHA0,
        beta0=BLEED_BETA0,
        gamma=CYCLE_GAMMA,
    )

    expected = cycle_posterior.point_estimate
    bleed = min(BLEED_MAX, max(BLEED_MIN, round(bleed_posterior.point_estimate)))
    ovulation = _ovulation_day(expected)
    fertile = (
        max(1, ovulation - 5),
        ovulation + 1,
    )

    forced_symptom = tracking_mode in {"unsure", "hormonal_contraception"}
    uncertain = (
        len(valid_lengths) >= 3
        and cycle_posterior.predictive_sd >= SYMPTOM_SD_THRESHOLD
    )
    symptom_mode = forced_symptom or uncertain

    if forced_symptom:
        reason = (
            "Cycle timing is not estimated in this mode; daily guidance "
            "uses the symptoms you report."
        )
    elif uncertain:
        reason = (
            "Recent cycle lengths vary enough that phase labels are hidden; "
            "guidance uses your logged state."
        )
    elif not valid_lengths:
        reason = (
            "Phase uses a population prior until enough of your cycles are logged."
        )
    else:
        reason = (
            "Phase uses your logged cycles with a forgetting prior; "
            "today's reported state takes priority."
        )

    latest_start = starts[-1] if starts else last_period_start
    return CycleModelState(
        cycle_posterior=cycle_posterior,
        bleed_posterior=bleed_posterior,
        observed_cycle_count=len(valid_lengths),
        valid_cycle_lengths=tuple(valid_lengths),
        excluded_cycle_count=excluded,
        last_period_start=latest_start,
        predicted_length=expected,
        predicted_bleed=float(bleed),
        ovulation_day=ovulation,
        fertile_window=fertile,
        symptom_mode=symptom_mode,
        reason=reason,
    )


def phase_for_day(
    state: CycleModelState,
    *,
    today: date,
) -> DayPhase:
    if state.symptom_mode:
        return DayPhase(
            phase=None,
            cycle_day=None,
            late_estimate=False,
            message=state.reason,
        )
    if state.last_period_start is None:
        return DayPhase(
            phase=None,
            cycle_day=None,
            late_estimate=False,
            message="Enter a period start date to estimate phase.",
        )
    if state.last_period_start > today:
        raise ValueError("Last period start cannot be in the future.")

    cycle_day = (today - state.last_period_start).days + 1
    expected = max(1, int(round(state.predicted_length)))
    bleed = int(round(state.predicted_bleed))
    ovulation = state.ovulation_day
    late = cycle_day > expected

    if cycle_day <= bleed:
        phase = "Menstrual"
    elif cycle_day < ovulation - 1:
        phase = "Follicular"
    elif ovulation - 1 <= cycle_day <= ovulation + 1:
        phase = "Ovulatory"
    else:
        phase = "Luteal"

    if late:
        phase = "Luteal"
        message = "Your period looks later than estimated."
    else:
        message = state.reason

    return DayPhase(
        phase=phase,
        cycle_day=cycle_day,
        late_estimate=late,
        message=message,
    )


def predicted_next_start(state: CycleModelState) -> date | None:
    if state.last_period_start is None:
        return None
    return state.last_period_start + timedelta(days=int(round(state.predicted_length)))


def sigmoid(value: float) -> float:
    if value >= 0:
        exp = math.exp(-value)
        return 1.0 / (1.0 + exp)
    exp = math.exp(value)
    return exp / (1.0 + exp)


def encode_readiness_features(
    *,
    sleep_hours: float,
    energy: int,
    pain: int,
    mood: str,
    phase: str | None,
) -> tuple[float, ...]:
    sleep_n = min(1.0, max(0.0, (float(sleep_hours) - 4.0) / 4.0))
    energy_n = (max(1, min(5, int(energy))) - 1) / 4.0
    painfree = 1.0 - (max(0, min(10, int(pain))) / 10.0)
    mood_n = MOOD_TO_N.get(mood, 0.5)
    one_hot = [0.0, 0.0, 0.0, 0.0]
    if phase in PHASES:
        one_hot[PHASES.index(phase)] = 1.0
    return (
        sleep_n,
        energy_n,
        painfree,
        mood_n,
        one_hot[0],
        one_hot[1],
        one_hot[2],
        one_hot[3],
        1.0,
    )


def default_readiness_weights() -> list[float]:
    return list(M2_W0)


def predict_readiness(
    weights: Sequence[float],
    features: Sequence[float],
) -> ReadinessResult:
    if len(weights) != len(M2_W0) or len(features) != len(M2_W0):
        raise ValueError("Readiness weights and features must have length 9.")
    z = sum(w * x for w, x in zip(weights, features))
    p_too_much = sigmoid(z)
    r_hat = 1.0 - p_too_much
    if r_hat >= TIER_AS_PLANNED:
        tier = "as_planned"
    elif r_hat >= TIER_REDUCE:
        tier = "reduce"
    else:
        tier = "recovery"
    return ReadinessResult(
        r_hat=r_hat,
        p_too_much=p_too_much,
        tier=tier,
        weights=tuple(float(w) for w in weights),
        features=tuple(float(x) for x in features),
    )


def update_readiness_weights(
    weights: Sequence[float],
    features: Sequence[float],
    *,
    label_too_much: bool,
    eta: float = M2_ETA,
) -> list[float]:
    """One online logistic update with ridge pull toward w0, then clip."""
    current = [float(w) for w in weights]
    x = [float(v) for v in features]
    result = predict_readiness(current, x)
    y = 1.0 if label_too_much else 0.0
    error = result.p_too_much - y
    updated: list[float] = []
    for index, (w, xi, w0) in enumerate(zip(current, x, M2_W0)):
        lam = M2_PHASE_LAMBDA if index in M2_PHASE_INDEX else M2_LAMBDA
        step = error * xi + lam * (w - w0)
        next_w = w - eta * step
        low = w0 - M2_CLIP
        high = w0 + M2_CLIP
        updated.append(min(high, max(low, next_w)))
    return updated


def readiness_plan_multiplier(tier: str) -> float:
    if tier == "as_planned":
        return 1.0
    if tier == "reduce":
        return 0.8
    return 0.0  # recovery session replaces the plan


def evaluate_escalation(
    *,
    today: date,
    checkins: Sequence[dict],
    cycle_lengths: Sequence[int] = (),
    positive_pregnancy_test: bool = False,
) -> tuple[str, ...]:
    """Fixed safety net. Missed escalation is not delegated to learned models."""
    alerts: list[str] = []
    ordered = sorted(
        (
            {
                **item,
                "checkin_date": (
                    date.fromisoformat(item["checkin_date"])
                    if isinstance(item["checkin_date"], str)
                    else item["checkin_date"]
                ),
            }
            for item in checkins
            if item.get("checkin_date") is not None
        ),
        key=lambda item: item["checkin_date"],
    )

    starts, _ = detect_period_starts(ordered)
    last_start = starts[-1] if starts else None
    if last_start and (today - last_start).days >= 90:
        alerts.append("No period has been reported for 90 or more days.")

    recent = [item for item in ordered if 0 <= (today - item["checkin_date"]).days <= 2]
    high_pain_days = {
        item["checkin_date"]
        for item in recent
        if int(item.get("pain") or 0) >= 8
    }
    if len(high_pain_days) >= 2:
        alerts.append("Pain of 8 or more was reported twice in three days.")

    heavy_streak = 0
    for item in ordered:
        flow = item.get("flow")
        if flow in {"Heavy", "Very heavy"}:
            heavy_streak += 1
            if heavy_streak >= 3:
                alerts.append("Heavy flow was reported three days in a row.")
                break
        else:
            heavy_streak = 0

    recent_lengths = list(cycle_lengths)[-4:]
    if len(recent_lengths) >= 4:
        outliers = sum(1 for length in recent_lengths if length < 21 or length > 35)
        if outliers >= 3:
            alerts.append(
                "Three of the last four cycles were shorter than 21 or longer than 35 days."
            )

    if positive_pregnancy_test:
        alerts.append("A positive pregnancy test was reported.")

    return tuple(alerts)


def cold_start_predictive_sd() -> float:
    return fit_nig(
        [],
        mu0=CYCLE_MU0,
        kappa0=CYCLE_KAPPA0,
        alpha0=CYCLE_ALPHA0,
        beta0=CYCLE_BETA0,
    ).predictive_sd
