"""Local 'What might help' knowledge base (Moss cut-ladder fallback).

Evidence chips must read exactly Established, Emerging, or Traditional.
Ayurveda/TCM entries are food and lifestyle only: no herbs, supplements, or dosing.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date


EVIDENCE_LABELS = ("Established", "Emerging", "Traditional")
LENSES = ("Medicine", "Ayurveda", "TCM")
SYMPTOMS = ("Cramps", "Low energy", "Mood", "Sleep", "Bloating")
PHASES = ("Menstrual", "Follicular", "Ovulatory", "Luteal", "All days")


@dataclass(frozen=True)
class HelpEntry:
    id: str
    phase: str
    lens: str
    symptom: str
    title: str
    body: str
    evidence: str
    source_domain: str
    source_url: str
    retrieved_at: str


# Curated, citeable lifestyle entries. Not medical advice.
HELP_ENTRIES: tuple[HelpEntry, ...] = (
    HelpEntry(
        id="med-cramps-heat",
        phase="Menstrual",
        lens="Medicine",
        symptom="Cramps",
        title="Heat and gentle movement for cramps",
        body=(
            "A warm pack on the lower abdomen and light walking are commonly "
            "used self-care options for menstrual cramps."
        ),
        evidence="Established",
        source_domain="acog.org",
        source_url="https://www.acog.org/womens-health/faqs/dysmenorrhea-painful-periods",
        retrieved_at="2026-10-01",
    ),
    HelpEntry(
        id="med-energy-sleep",
        phase="All days",
        lens="Medicine",
        symptom="Low energy",
        title="Protect a consistent sleep window",
        body=(
            "Keeping a steady sleep and wake time supports daytime energy. "
            "Logged sleep takes priority over any cycle prior."
        ),
        evidence="Established",
        source_domain="cdc.gov",
        source_url="https://www.cdc.gov/sleep/about/index.html",
        retrieved_at="2026-10-01",
    ),
    HelpEntry(
        id="med-mood-move",
        phase="Luteal",
        lens="Medicine",
        symptom="Mood",
        title="Short outdoor walks",
        body=(
            "Brief outdoor walks are a practical mood-support habit when "
            "energy allows; skip them on high-pain days."
        ),
        evidence="Emerging",
        source_domain="nih.gov",
        source_url="https://www.ncbi.nlm.nih.gov/books/NBK279054/",
        retrieved_at="2026-10-01",
    ),
    HelpEntry(
        id="ayu-bloating-warm",
        phase="Menstrual",
        lens="Ayurveda",
        symptom="Bloating",
        title="Warm, easy-to-digest meals",
        body=(
            "Traditional guidance favors warm, simple cooked meals and "
            "steady hydration. This is lifestyle framing only."
        ),
        evidence="Traditional",
        source_domain="nccih.nih.gov",
        source_url="https://www.nccih.nih.gov/health/ayurvedic-medicine-in-depth",
        retrieved_at="2026-10-01",
    ),
    HelpEntry(
        id="tcm-sleep-routine",
        phase="All days",
        lens="TCM",
        symptom="Sleep",
        title="Wind-down before bed",
        body=(
            "Traditional lifestyle advice emphasizes a calm evening routine "
            "and an earlier wind-down. No herbs or dosing are suggested here."
        ),
        evidence="Traditional",
        source_domain="nccih.nih.gov",
        source_url="https://www.nccih.nih.gov/health/traditional-chinese-medicine-what-you-need-to-know",
        retrieved_at="2026-10-01",
    ),
    HelpEntry(
        id="med-follicular-energy",
        phase="Follicular",
        lens="Medicine",
        symptom="Low energy",
        title="Build training gradually",
        body=(
            "When energy is returning, increase training load gradually and "
            "keep today's logged fatigue as the override."
        ),
        evidence="Emerging",
        source_domain="acsm.org",
        source_url="https://www.acsm.org/education-resources/trending-topics-resources/physical-activity-guidelines",
        retrieved_at="2026-10-01",
    ),
    HelpEntry(
        id="med-cramps-all",
        phase="All days",
        lens="Medicine",
        symptom="Cramps",
        title="Gentle heat and rest",
        body=(
            "Warmth on the lower abdomen and easy rest are common self-care "
            "options for cramp discomfort."
        ),
        evidence="Established",
        source_domain="acog.org",
        source_url="https://www.acog.org/womens-health/faqs/dysmenorrhea-painful-periods",
        retrieved_at="2026-10-01",
    ),
    HelpEntry(
        id="med-mood-all",
        phase="All days",
        lens="Medicine",
        symptom="Mood",
        title="Steady daily rhythm",
        body=(
            "A consistent sleep and meal rhythm supports mood on most days."
        ),
        evidence="Emerging",
        source_domain="nih.gov",
        source_url="https://www.ncbi.nlm.nih.gov/books/NBK279054/",
        retrieved_at="2026-10-01",
    ),
    HelpEntry(
        id="med-sleep-all",
        phase="All days",
        lens="Medicine",
        symptom="Sleep",
        title="Wind-down routine",
        body=(
            "A calm evening routine and steady bedtime support better sleep."
        ),
        evidence="Established",
        source_domain="cdc.gov",
        source_url="https://www.cdc.gov/sleep/about/index.html",
        retrieved_at="2026-10-01",
    ),
    HelpEntry(
        id="med-bloating-all",
        phase="All days",
        lens="Medicine",
        symptom="Bloating",
        title="Gentle movement and hydration",
        body=(
            "Light walking and steady hydration can ease bloating for many people."
        ),
        evidence="Emerging",
        source_domain="nccih.nih.gov",
        source_url="https://www.nccih.nih.gov/",
        retrieved_at="2026-10-01",
    ),
    HelpEntry(
        id="ayu-cramps-warm",
        phase="All days",
        lens="Ayurveda",
        symptom="Cramps",
        title="Warmth and gentle routine",
        body=(
            "Traditional guidance favors warmth and a calm daily routine. "
            "This is lifestyle framing only."
        ),
        evidence="Traditional",
        source_domain="nccih.nih.gov",
        source_url="https://www.nccih.nih.gov/health/ayurvedic-medicine-in-depth",
        retrieved_at="2026-10-01",
    ),
    HelpEntry(
        id="tcm-bloating-warm",
        phase="All days",
        lens="TCM",
        symptom="Bloating",
        title="Warm foods and calm evenings",
        body=(
            "Traditional lifestyle advice favors warm foods and a calm evening. "
            "No herbs or dosing are suggested here."
        ),
        evidence="Traditional",
        source_domain="nccih.nih.gov",
        source_url="https://www.nccih.nih.gov/health/traditional-chinese-medicine-what-you-need-to-know",
        retrieved_at="2026-10-01",
    ),
)


def filter_help(
    *,
    phase: str | None,
    lens: str,
    symptom: str,
    symptom_mode: bool = False,
) -> list[HelpEntry]:
    if lens not in LENSES or symptom not in SYMPTOMS:
        return []
    phase_key = "All days" if symptom_mode or not phase else phase
    matched = [
        entry
        for entry in HELP_ENTRIES
        if entry.lens == lens
        and entry.symptom == symptom
        and entry.phase in {phase_key, "All days"}
        and entry.evidence in EVIDENCE_LABELS
    ]
    if not matched:
        matched = [
            entry
            for entry in HELP_ENTRIES
            if entry.symptom == symptom
            and entry.phase in {"All days"}
            and entry.evidence in EVIDENCE_LABELS
        ]
    return matched


def pick_daily_help(
    *,
    phase: str | None,
    day_index: int,
    symptom_mode: bool = False,
) -> HelpEntry | None:
    pool = [
        entry
        for entry in HELP_ENTRIES
        if entry.phase in {"All days", phase or "All days"}
        or (symptom_mode and entry.phase == "All days")
    ]
    if not pool:
        return None
    return pool[day_index % len(pool)]
