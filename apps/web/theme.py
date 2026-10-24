"""Cadence theme."""

from __future__ import annotations


def star_positions_for_session() -> list[tuple[float, float, float, float, float]]:
    import random

    rng = random.Random(20260424)
    sizes = (1.0, 1.2, 1.5, 2.0, 2.5)
    stars = []
    for _ in range(40):
        stars.append(
            (
                rng.random() * 100.0,
                rng.random() * 100.0,
                sizes[rng.randrange(len(sizes))],
                round(0.15 + rng.random() * 0.45, 3),
                round(rng.random() * 6.0, 3),
            )
        )
    return stars


def inject_theme(star_positions):
    import streamlit as st

    stars_html = "".join(
        (
            f'' + f'<span class="phase-star" style="left:{x:.3f}%;top:{y:.3f}%;'
            f'width:{size:.1f}px;height:{size:.1f}px;opacity:{opacity:.3f};'
            f'animation-delay:{delay:.3f}s;"></span>'
        )
        for x, y, size, opacity, delay in star_positions
    )
    st.markdown(
        f"""
        <div class="phase-starfield" aria-hidden="true">{stars_html}</div>
        <style>
        :root {{
            color-scheme: dark;
            --cream: #F3E9D2;
            --cream-soft: rgba(243,233,210,.75);
            --pale-gold: #E9D49A;
            --gold: #C9A24B;
            --cherry: #9B1B30;
            --crimson: #5A0F1C;
            --rose: #E7879A;
            --glass: rgba(251,244,228,.10);
            --glass-strong: rgba(90,15,28,.72);
            --border-gold: rgba(233,212,154,.35);
            --shadow: rgba(30,0,10,.35);
        }}
        .stApp, [data-testid="stAppViewContainer"] {{
            background:
                radial-gradient(circle at 18% 8%, rgba(201,162,75,.18), transparent 34%),
                radial-gradient(circle at 72% 34%, rgba(231,135,154,.22), transparent 38%),
                radial-gradient(circle at 50% 96%, rgba(233,212,154,.22), transparent 40%),
                linear-gradient(180deg, #3B0A14 0%, #5A0F1C 22%, #7C1730 48%, #9B2A40 70%, #8E2B45 100%);
            background-attachment: fixed;
            color: var(--cream) !important;
            min-height: 100vh;
        }}
        .phase-starfield {{
            position: fixed;
            inset: 0;
            pointer-events: none;
            z-index: 0;
            overflow: hidden;
        }}
        .phase-star {{
            position: absolute;
            border-radius: 999px;
            background: radial-gradient(circle, #F3E9D2 0%, #E9D49A 70%, transparent 100%);
            box-shadow: 0 0 6px rgba(233,212,154,.45);
            animation: phase-twinkle 4.5s ease-in-out infinite;
        }}
        @keyframes phase-twinkle {{
            0%, 100% {{ opacity: .18; transform: scale(.9); }}
            50% {{ opacity: .62; transform: scale(1.08); }}
        }}
""",
        unsafe_allow_html=True,
    )
    st.markdown(
        """
        <style>
        [data-testid="stVerticalBlockBorderWrapper"], .glass-card {
            background: rgba(251,244,228,.10) !important;
            border: 1px solid rgba(233,212,154,.35) !important;
            border-radius: 1.25rem !important;
            box-shadow: 0 10px 30px rgba(30,0,10,.35), inset 0 1px 0 rgba(255,255,255,.12) !important;
            backdrop-filter: blur(14px) saturate(120%);
            -webkit-backdrop-filter: blur(14px) saturate(120%);
        }
        @supports not (backdrop-filter: blur(1px)) {
            [data-testid="stVerticalBlockBorderWrapper"], .glass-card {
                background: rgba(90,15,28,.72) !important;
            }
        }
        .stApp, .stApp p, .stApp label, .stApp li,
        .stApp [data-testid="stMarkdownContainer"],
        .stApp [data-testid="stWidgetLabel"],
        .stApp [data-testid="stCaptionContainer"] {
            color: var(--cream) !important;
            font-family: "Nunito", "Avenir Next", "Segoe UI", sans-serif;
        }
        h1, h2, h3, h4 {
            color: var(--cream) !important;
            font-family: "Cormorant Garamond", "Iowan Old Style", "Palatino Linotype", Georgia, serif !important;
            letter-spacing: .02em;
        }
        .phase-label {
            color: var(--pale-gold) !important;
            text-transform: uppercase;
            letter-spacing: .16em;
            font-size: .72rem;
            font-weight: 700;
        }
        div.stButton > button[kind="primary"] {
            background: linear-gradient(180deg, #B12A45 0%, #7C1730 100%) !important;
            color: var(--cream) !important;
            border: 1px solid var(--gold) !important;
            border-radius: 999px !important;
            box-shadow: 0 8px 18px rgba(30,0,10,.35), inset 0 1px 0 rgba(255,255,255,.18);
            transform: scale(1);
            transition: transform 120ms ease;
        }
        div.stButton > button[kind="primary"]:active { transform: scale(.96); }
        div.stButton > button[kind="secondary"] {
            background: rgba(251,244,228,.10) !important;
            color: var(--cream) !important;
            border: 1px solid var(--gold) !important;
            border-radius: 999px !important;
            backdrop-filter: blur(10px);
        }
        .phase-chip {
            display: inline-block;
            padding: .25rem .65rem;
            border-radius: 999px;
            background: rgba(233,212,154,.16);
            border: 1px solid var(--gold);
            color: var(--cream);
            font-size: .8rem;
        }
        .phase-card-accent {
            border: 1px solid transparent !important;
            border-image: linear-gradient(135deg, #9B2A40, #C9A24B) 1 !important;
        }
        header, #MainMenu, footer, [data-testid="stToolbar"], [data-testid="stDeployButton"] {
            display: none !important;
        }
        [data-testid="stMainBlockContainer"] {
            max-width: 720px !important;
            padding-top: .75rem !important;
            padding-bottom: 5rem !important;
        }
        @media (prefers-reduced-motion: reduce) {
            .phase-star, .phase-ripple, .phase-pulse, .phase-drift { animation: none !important; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        """
        <style>
        .tide-drift { animation: tide-drift 6s linear infinite; }
        @keyframes tide-drift {
            0% { transform: translateX(0); }
            100% { transform: translateX(6px); }
        }
        .phase-pulse { animation: phase-pulse 2s ease-in-out infinite; transform-origin: center; }
        @keyframes phase-pulse {
            0%, 100% { opacity: .7; }
            50% { opacity: 1; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
