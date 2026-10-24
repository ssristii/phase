"""Deterministic cycle statistics for the clinician report.

Never use an LLM to compute these values. Gemini may only narrate after
numbers are calculated here.
"""

from __future__ import annotations

import math
import statistics
from dataclasses import dataclass
from datetime import date
from typing import Sequence

from models import build_cycle_model, detect_period_starts


@dataclass(frozen=True)
class CycleStats:
    cycles_logged: int
    mean: float | None
    median: float | None
    mode: float | None
    range_span: float | None
    stdev: float | None
    lengths: tuple[int, ...]
    flags: tuple[str, ...]
    bar_counts: tuple[tuple[int, int], ...]  # (length, count) sorted


def _mode(values: Sequence[float]) -> float | None:
    if not values:
        return None
    try:
        return float(statistics.mode(values))
    except statistics.StatisticsError:
        # Multimodal: pick the smallest of the most frequent values.
        counts: dict[float, int] = {}
        for value in values:
            counts[value] = counts.get(value, 0) + 1
        top = max(counts.values())
        return min(value for value, count in counts.items() if count == top)


def compute_cycle_stats(
    checkins: Sequence[dict],
    *,
    today: date | None = None,
) -> CycleStats:
    today = today or date.today()
    starts, _ = detect_period_starts(checkins)
    state = build_cycle_model(checkins, today=today, tracking_mode="period_date")
    lengths = list(state.valid_cycle_lengths)
    flags: list[str] = []
    if state.excluded_cycle_count:
        flags.append(
            f"{state.excluded_cycle_count} possible missed or invalid cycle "
            "length(s) excluded from fitting."
        )
    if lengths and (max(lengths) - min(lengths)) >= 7:
        flags.append("Cycle length range is 7 or more days.")
    if len(lengths) >= 4:
        outliers = sum(1 for length in lengths[-4:] if length < 21 or length > 35)
        if outliers >= 3:
            flags.append(
                "Three of the last four valid cycles were outside 21 to 35 days."
            )

    if not lengths:
        return CycleStats(
            cycles_logged=0,
            mean=None,
            median=None,
            mode=None,
            range_span=None,
            stdev=None,
            lengths=(),
            flags=tuple(flags),
            bar_counts=(),
        )

    values = [float(length) for length in lengths]
    mean = statistics.fmean(values)
    median = float(statistics.median(values))
    mode = _mode(values)
    range_span = max(values) - min(values)
    stdev = float(statistics.pstdev(values)) if len(values) > 1 else 0.0

    counts: dict[int, int] = {}
    for length in lengths:
        counts[length] = counts.get(length, 0) + 1
    bar_counts = tuple(sorted(counts.items()))

    return CycleStats(
        cycles_logged=len(lengths),
        mean=mean,
        median=median,
        mode=mode,
        range_span=range_span,
        stdev=stdev,
        lengths=tuple(lengths),
        flags=tuple(flags),
        bar_counts=bar_counts,
    )


def format_stat(value: float | None, *, digits: int = 1) -> str:
    if value is None:
        return "—"
    if math.isclose(value, round(value)):
        return str(int(round(value)))
    return f"{value:.{digits}f}"


def build_report_pdf_bytes(
    stats: CycleStats,
    *,
    title: str = "Cadence summary",
    synthetic: bool = False,
) -> bytes:
    """Minimal PDF built without third-party deps (plain layout is intentional)."""
    lines = [
        title,
        "Self-reported data",
    ]
    if synthetic:
        lines.append("Synthetic demo data")
    lines.extend(
        [
            f"Cycles logged: {stats.cycles_logged}",
            f"Mean: {format_stat(stats.mean)}",
            f"Median: {format_stat(stats.median)}",
            f"Mode: {format_stat(stats.mode)}",
            f"Range: {format_stat(stats.range_span)}",
            f"Standard deviation: {format_stat(stats.stdev)}",
        ]
    )
    if stats.flags:
        lines.append("Flags: " + "; ".join(stats.flags))
    else:
        lines.append("Flags: none")
    if stats.bar_counts:
        bars = ", ".join(f"{length}d x{count}" for length, count in stats.bar_counts)
        lines.append(f"Length counts: {bars}")

    content_lines = ["BT /F1 12 Tf 50 750 Td 14 TL"]
    for index, line in enumerate(lines):
        safe = (
            line.replace("\\", "\\\\")
            .replace("(", "\\(")
            .replace(")", "\\)")
        )
        if index == 0:
            content_lines.append(f"({safe}) Tj")
        else:
            content_lines.append(f"T* ({safe}) Tj")
    content_lines.append("ET")
    stream = "\n".join(content_lines).encode("latin-1", errors="replace")

    objects: list[bytes] = []
    objects.append(b"1 0 obj<< /Type /Catalog /Pages 2 0 R >>endobj\n")
    objects.append(b"2 0 obj<< /Type /Pages /Kids [3 0 R] /Count 1 >>endobj\n")
    objects.append(
        b"3 0 obj<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Contents 4 0 R /Resources<< /Font<< /F1 5 0 R >> >> >>endobj\n"
    )
    objects.append(
        f"4 0 obj<< /Length {len(stream)} >>stream\n".encode("ascii")
        + stream
        + b"\nendstream\nendobj\n"
    )
    objects.append(
        b"5 0 obj<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>endobj\n"
    )

    buffer = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for obj in objects:
        offsets.append(len(buffer))
        buffer.extend(obj)
    xref_pos = len(buffer)
    buffer.extend(f"xref\n0 {len(offsets)}\n".encode("ascii"))
    buffer.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        buffer.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    buffer.extend(
        f"trailer<< /Size {len(offsets)} /Root 1 0 R >>\n"
        f"startxref\n{xref_pos}\n%%EOF\n".encode("ascii")
    )
    return bytes(buffer)
