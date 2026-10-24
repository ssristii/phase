"""Cadence SVG generators."""

from __future__ import annotations

import math


def _hex_to_rgb(value: str) -> tuple[int, int, int]:
    value = value.lstrip("#")
    return (int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16))


def _rgb_to_hex(rgb: tuple[int, int, int]) -> str:
    return "#" + "".join(f"{max(0, min(255, int(round(c)))):02X}" for c in rgb)


def _lerp_color(a: str, b: str, t: float) -> str:
    t = max(0.0, min(1.0, t))
    ar, ag, ab = _hex_to_rgb(a)
    br, bg, bb = _hex_to_rgb(b)
    return _rgb_to_hex(
        (ar + (br - ar) * t, ag + (bg - ag) * t, ab + (bb - ab) * t)
    )


def _tide_level(day: int, cycle_len: int, bleed_len: int, ovulation_day: int) -> float:
    b = max(1, bleed_len)
    o = ovulation_day
    n = max(1, cycle_len)
    d = day
    if d <= b:
        return 0.15 + 0.10 * (d - 1) / max(b - 1, 1)
    if d <= o - 2:
        span = max(1, (o - 2) - (b + 1) + 1)
        frac = (d - (b + 1)) / max(span - 1, 1)
        return 0.30 + (0.90 - 0.30) * frac
    if d <= o + 1:
        return 1.0
    span = max(1, n - (o + 2) + 1)
    frac = (d - (o + 2)) / max(span - 1, 1)
    return 0.88 + (0.20 - 0.88) * frac


def _phase_name(day: int, bleed_len: int, ovulation_day: int, cycle_len: int) -> str:
    if day <= bleed_len:
        return "Menstrual"
    if day <= ovulation_day - 2:
        return "Follicular"
    if day <= ovulation_day + 1:
        return "Ovulatory"
    return "Luteal"


def _color_for_day(day: int, bleed_len: int, ovulation_day: int, cycle_len: int) -> str:
    stops = [
        (1, "#C42B48"),
        (max(1, bleed_len), "#E0637A"),
        (max(1, bleed_len + 1), "#E8A07A"),
        (max(1, ovulation_day - 2), "#C9A24B"),
        (max(1, ovulation_day), "#F3DC9A"),
        (max(1, ovulation_day + 2), "#E3A0A8"),
        (max(1, cycle_len), "#B8587A"),
        (cycle_len + 1, "#C42B48"),
    ]
    # Remove duplicate days, keeping the last color for that day.
    unique: dict[int, str] = {}
    for d, color in stops:
        unique[d] = color
    items = sorted(unique.items())
    if day <= items[0][0]:
        return items[0][1]
    if day >= items[-1][0]:
        return items[-1][1]
    for i in range(len(items) - 1):
        d0, c0 = items[i]
        d1, c1 = items[i + 1]
        if d0 <= day <= d1:
            span = max(1, d1 - d0)
            return _lerp_color(c0, c1, (day - d0) / span)
    return items[-1][1]


def tide_wheel_svg(
    day,
    cycle_len,
    bleed_len,
    ovulation_day,
    mode,
    levels=None,
    phase_name_override=None,
):
    symptom = str(mode).lower().startswith("sym")
    n = 7 if symptom else max(21, min(35, int(round(cycle_len or 28))))
    # Allow caller to pass an explicit length in symptom mode.
    if not symptom:
        n = max(1, int(round(cycle_len or 28)))
        n = min(35, max(21, n))
    try:
        current_day = int(day) if day is not None else None
    except (TypeError, ValueError):
        current_day = None
    if symptom:
        current_day = n
    b = int(bleed_len or 0)
    o = int(ovulation_day or max(1, n - 14))
    r_base = max(7.0, min(11.0, (2 * math.pi * 140.0 / n) * 0.32))
    parts = []
    aria = "Cycle wheel, day %d of %d" % (current_day or 0, n)
    if not symptom:
        aria += ", " + _phase_name(current_day or 1, b, o, n)
    parts.append(
        '<svg viewBox="0 0 360 360" width="100%" height="auto" role="img" '
        'aria-label="' + aria + '" xmlns="http://www.w3.org/2000/svg">'
    )
    # Ambience glow and ripples.
    parts.append(
        '<defs><radialGradient id="wheel-glow" cx="50%" cy="50%"><stop offset="0%" stop-color="rgba(233,212,154,.25)"/><stop offset="100%" stop-color="transparent"/></radialGradient></defs>'
    )
    parts.append('<circle cx="180" cy="180" r="150" fill="url(#wheel-glow)" opacity=".55"/>')
    for rr in (150, 120, 90):
        parts.append(f'<circle cx="180" cy="180" r="{rr}" fill="none" stroke="rgba(233,212,154,.18)" stroke-width="1"/>')
    # Glyphs.
    for i in range(n):
        di = i + 1
        angle = -math.pi / 2 + (2 * math.pi * i / n)
        cx = 180 + 140 * math.cos(angle)
        cy = 180 + 140 * math.sin(angle)
        is_today = (not symptom and current_day == di) or (symptom and di == n)
        radius = 16.0 if is_today else r_base
        if symptom:
            radius = max(radius, 10.0)
        # water level
        if symptom:
            if levels and i < len(levels) and levels[i] is not None:
                try:
                    lvl = max(0.0, min(1.0, (float(levels[i]) - 1.0) / 4.0))
                except (TypeError, ValueError):
                    lvl = 0.0
                filled = True
            else:
                lvl = 0.0
                filled = False
        else:
            lvl = _tide_level(di, n, b, o)
            filled = di < (current_day or 0) or is_today
            # future days outline only
            if current_day is not None and di > current_day:
                filled = False
        color = _color_for_day(di, b, o, n) if not symptom else "#C9A24B"
        phase = _phase_name(di, b, o, n) if not symptom else "day"
        # clip path
        clip_id = f"tide-clip-{i}"
        parts.append(f'<defs><clipPath id="{clip_id}"><circle cx="{cx:.1f}" cy="{cy:.1f}" r="{radius:.1f}"/></clipPath></defs>')
        # water body
        if filled:
            ys = radius - 2 * radius * lvl
            # sample wave across glyph
            steps = 12
            pts = []
            for s in range(steps + 1):
                x_local = -radius + (2 * radius * s / steps)
                y_wave = ys + 0.22 * radius * math.sin(2 * math.pi * x_local / (1.1 * radius) + di * 0.35)
                pts.append((x_local, y_wave))
            path = f"M {pts[0][0]:.1f} {pts[0][1]:.1f}"
            for x_local, y_wave in pts[1:]:
                path += f" L {x_local:.1f} {y_wave:.1f}"
            path += f" L {radius:.1f} {radius:.1f} L {-radius:.1f} {radius:.1f} Z"
            parts.append(
                f'<g class="tide-drift" style="animation-delay:{di*0.15:.2f}s">'
                f'<g transform="translate({cx:.1f},{cy:.1f})" clip-path="url(#{clip_id})">'
                f'<path d="{path}" fill="{color}" opacity=".92"/>'
                f'</g></g>'
            )
        else:
            # outline with thin wave line
            ys = radius - 2 * radius * lvl
            x0 = -radius
            x1 = radius
            y0 = ys + 0.22 * radius * math.sin(2 * math.pi * x0 / (1.1 * radius) + di * 0.35)
            y1 = ys + 0.22 * radius * math.sin(2 * math.pi * x1 / (1.1 * radius) + di * 0.35)
            parts.append(
                f'<g transform="translate({cx:.1f},{cy:.1f})">'
                f'<path d="M {x0:.1f} {y0:.1f} Q 0 {ys:.1f} {x1:.1f} {y1:.1f}" fill="none" stroke="{color}" stroke-width="1.2" opacity=".55"/>'
                f'</g>'
            )
        # outline circle
        parts.append(
            f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{radius:.1f}" fill="none" stroke="rgba(233,212,154,.6)" stroke-width="1"/>'
        )
        if is_today:
            parts.append(
                f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{radius + 4:.1f}" fill="none" stroke="#F3E9D2" stroke-width="2" class="phase-pulse"/>'
            )
        # title
        parts.append(f'<title>Day {di}, {phase}</title>')
    # Center text
    if not symptom:
        pname = phase_name_override or (_phase_name(current_day or 1, b, o, n) if current_day else "")
        parts.append(
            f'<text x="180" y="170" text-anchor="middle" fill="#F3E9D2" font-family="Cormorant Garamond, Georgia, serif" font-size="26">{pname}</text>'
        )
    parts.append(
        f'<text x="180" y="198" text-anchor="middle" fill="rgba(243,233,210,.75)" font-family="Nunito, sans-serif" font-size="11" letter-spacing="2">DAY {current_day or 0} OF {n}</text>'
    )
    if not symptom:
        if current_day is not None and current_day > n:
            k_text = "Your period looks later than estimated"
        else:
            k = max(0, n - (current_day or 0))
            k_text = f"Period in about {k} days"
        parts.append(
            f'<text x="180" y="220" text-anchor="middle" fill="rgba(243,233,210,.75)" font-family="Nunito, sans-serif" font-size="10" letter-spacing="1">{k_text}</text>'
        )
    parts.append('</svg>')
    return "".join(parts)
