import json
import os
import re
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import streamlit as st
from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.errors import PyMongoError

from models import build_cycle_model, default_readiness_weights
from persistence import (
    add_phase_heart,
    authenticate_account,
    create_account,
    count_phase_hearts,
    get_checkin,
    get_phase_lock,
    get_readiness_weights,
    list_checkins,
    lock_phase_plan,
    save_checkin,
    save_phase_workout_plan,
    stored_profile,
    PROFILE_VERSION,
)
from phase_engine import (
    evaluate_safety,
    predict_cycle,
    weekly_workout_schedule,
)

from help_kb import filter_help, pick_daily_help, SYMPTOMS, LENSES
from stats import compute_cycle_stats, build_report_pdf_bytes, format_stat

try:
    from inmemory_db import connect_in_memory
except Exception:
    connect_in_memory = None


@st.cache_resource
def connect_in_memory_cached(database_name: str):
    if connect_in_memory is None:
        return None
    return connect_in_memory(database_name)


load_dotenv(Path(__file__).with_name(".env"))
TODAY = date.today()
PHASES = ("Menstrual", "Follicular", "Ovulatory", "Luteal")
GOALS = ("Strength", "Muscle", "Endurance", "General fitness", "Energy")
WORKOUT_SPLITS = (
    "Full body",
    "Upper/Lower",
    "Push/Pull/Legs",
    "Body-part split",
    "Not sure",
)
TRACKING_MODES = (
    "I know my last period start",
    "I'm not sure",
    "On hormonal contraception",
)
FLOWS = ("None", "Spotting", "Light", "Moderate", "Heavy", "Very heavy")
MOODS = ("Low", "Okay", "Good", "Anxious", "Irritable")
TRACKING_MODE_VALUES = {
    TRACKING_MODES[0]: "period_date",
    TRACKING_MODES[1]: "unsure",
    TRACKING_MODES[2]: "hormonal_contraception",
}
CHECKIN_INPUT_KEYS = (
    "checkin-flow",
    "checkin-mood",
    "checkin-energy",
    "checkin-sleep",
    "checkin-pain",
    "checkin-workout-done",
    "checkin-severe-pain",
    "checkin-irregular",
    "checkin-pregnancy",
)
EMOJI_PATTERN = re.compile(
    "[\U0001F300-\U0001FAFF\U0001F1E6-\U0001F1FF"
    "\u2600-\u27BF\uFE0F\u200D]"
)


def strip_emojis(text: str) -> str:
    return EMOJI_PATTERN.sub("", text)


# Conservative spoken-name scrub before any storage of free text.
NAME_PATTERN = re.compile(
    r"\b(?:my name is|i am|i'm|this is)\s+[A-Z][a-z]{1,30}\b",
    re.IGNORECASE,
)


def strip_spoken_names(text: str) -> str:
    return NAME_PATTERN.sub(lambda match: match.group(0).split()[0] + " [name]", text)


def clean_voice_transcript() -> None:
    st.session_state["voice_transcript"] = strip_spoken_names(
        strip_emojis(st.session_state.get("voice_transcript", ""))
    )


def clear_voice_text() -> None:
    st.session_state.pop("voice_transcript", None)
    st.session_state.pop("voice_extracted", None)
    st.session_state.pop("voice_transcribed", None)
    st.session_state.pop("voice_g1_result", None)
    st.session_state.pop("voice_confirm_fields", None)
    st.session_state.pop("voice_field_provenance", None)
    discard_g1_audio()


def discard_audio_capture() -> None:
    """Reset the recorder widget. Does not drop G1 WAV held for extraction."""
    nonce = int(st.session_state.get("audio_nonce", 0))
    st.session_state.pop(f"audio_{nonce}", None)
    st.session_state.pop("voice-upload", None)
    st.session_state["audio_nonce"] = nonce + 1


def discard_g1_audio() -> None:
    st.session_state.pop("voice_wav_bytes", None)
    st.session_state.pop("voice_wav_type", None)


# Streamlit 1.53.1 signature: set_page_config(page_title, page_icon, layout, initial_sidebar_state, menu_items).
st.set_page_config(
    page_title="Cadence",
    page_icon=None,
    layout="centered",
    initial_sidebar_state="collapsed",
)
st.markdown(
    """
    <style>
    :root {
        color-scheme: light;
        --cherry: #9B1B30;
        --crimson: #5A0F1C;
        --gold: #C9A24B;
        --champagne: #F3E9D2;
        --parchment: #F3E9D2;
        --mahogany: #5A0F1C;
        --espresso: #2A1A14;
        --taupe: #6E5B54;
    }
    .stApp, [data-testid="stAppViewContainer"] {
        background:
            url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='200' height='200'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='2' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='0.035'/%3E%3C/svg%3E"),
            radial-gradient(ellipse at 50% 0%, rgba(243, 229, 171, 0.52), transparent 58%),
            radial-gradient(ellipse at 50% 100%, rgba(110, 91, 84, 0.10), transparent 62%),
            var(--parchment);
        color: var(--espresso) !important;
    }
    [data-testid="stHeader"], [data-testid="stToolbar"] {
        background: var(--parchment) !important;
        color: var(--espresso) !important;
    }
    header, #MainMenu, footer, [data-testid="stToolbar"],
    [data-testid="stDeployButton"] { display: none !important; }
    [data-testid="stMainBlockContainer"] {
        max-width: 560px !important;
        padding-top: 1.5rem !important;
        padding-bottom: 2rem !important;
    }
    [data-testid="stSidebar"] {
        background: linear-gradient(160deg, #F3E5AB, var(--parchment) 55%, #E8DDC9);
        border-right: 1px solid rgba(139, 30, 38, 0.22);
    }
    .stApp, .stApp p, .stApp label, .stApp li,
    .stApp [data-testid="stMarkdownContainer"],
    .stApp [data-testid="stWidgetLabel"],
    .stApp [data-testid="stCaptionContainer"],
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] label {
        color: var(--espresso) !important;
        font-family: "Cormorant Garamond", "Iowan Old Style", "Palatino Linotype", Georgia, serif;
        font-size: 1.13rem;
        line-height: 1.55;
    }
    h1, h2, h3, h4 {
        color: var(--cherry) !important;
        font-family: "Playfair Display", "Iowan Old Style", "Palatino Linotype", Georgia, serif !important;
        letter-spacing: 0.015em;
    }
    h1 { font-size: 2.7rem !important; }
    h2 { font-size: 2.15rem !important; }
    h3 { font-size: 1.65rem !important; }
    [data-testid="stWidgetLabel"] p { font-weight: 700 !important; }
    [data-testid="stCaptionContainer"] p {
        color: var(--taupe) !important;
        font-size: 1rem !important;
    }
    .phase-brand {
        position: relative;
        margin: 0.35rem 0 2rem;
        padding: 1rem 1.4rem 0.9rem;
        text-align: center;
        border: 3px double var(--gold);
        outline: 1px solid rgba(212, 175, 55, 0.38);
        outline-offset: 4px;
        background: rgba(247, 242, 231, 0.7);
        box-shadow: 0 8px 22px rgba(43, 27, 23, 0.09);
    }
    .phase-brand-title {
        color: var(--cherry);
        font-family: "Playfair Display", "Iowan Old Style", Georgia, serif;
        font-size: clamp(2.1rem, 8vw, 3.2rem);
        font-weight: 700;
        letter-spacing: 0.16em;
        line-height: 1.15;
    }
    .phase-brand-subtitle {
        margin-top: 0.2rem;
        color: var(--taupe);
        font-family: "Cormorant Garamond", "Palatino Linotype", Georgia, serif;
        font-size: 1.08rem;
        font-style: italic;
        letter-spacing: 0.035em;
    }
    .phase-brand-divider {
        display: flex;
        align-items: center;
        gap: 0.65rem;
        width: min(21rem, 85%);
        margin: 0.45rem auto 0;
        color: var(--gold);
        font-size: 0.9rem;
    }
    .phase-brand-divider::before, .phase-brand-divider::after {
        content: "";
        flex: 1;
        height: 1px;
        background: linear-gradient(90deg, transparent, var(--gold), transparent);
    }
    [data-testid="stVerticalBlockBorderWrapper"] {
        background: linear-gradient(145deg, #38231D, var(--mahogany) 60%, #241612);
        border: 1px solid var(--gold) !important;
        border-radius: 1.15rem !important;
        box-shadow: 0 10px 25px rgba(43, 27, 23, 0.17), inset 0 1px rgba(243, 229, 171, 0.08);
        position: relative;
        overflow: visible;
        transition: transform 180ms ease, box-shadow 180ms ease;
    }
    [data-testid="stVerticalBlockBorderWrapper"]:hover {
        transform: translateY(-2px);
        box-shadow: 0 16px 32px rgba(43, 27, 23, 0.24), inset 0 1px rgba(243, 229, 171, 0.12);
    }
    @media (prefers-reduced-motion: reduce) {
        [data-testid="stVerticalBlockBorderWrapper"] { transition: none; }
        [data-testid="stVerticalBlockBorderWrapper"]:hover { transform: none; }
    }
    [data-testid="stVerticalBlockBorderWrapper"]::before,
    [data-testid="stVerticalBlockBorderWrapper"]::after {
        position: absolute;
        color: var(--gold);
        font-size: 1.1rem;
        opacity: 0.75;
        line-height: 1;
        pointer-events: none;
    }
    [data-testid="stVerticalBlockBorderWrapper"]::before {
        content: "·";
        top: 0.4rem;
        left: 0.65rem;
    }
    [data-testid="stVerticalBlockBorderWrapper"]::after {
        content: "·";
        bottom: 0.4rem;
        right: 0.65rem;
        transform: rotate(180deg);
    }
    [data-testid="stVerticalBlockBorderWrapper"] p,
    [data-testid="stVerticalBlockBorderWrapper"] li,
    [data-testid="stVerticalBlockBorderWrapper"] label,
    [data-testid="stVerticalBlockBorderWrapper"] [data-testid="stMarkdownContainer"],
    [data-testid="stVerticalBlockBorderWrapper"] [data-testid="stWidgetLabel"] {
        color: var(--parchment) !important;
    }
    [data-testid="stVerticalBlockBorderWrapper"] h1,
    [data-testid="stVerticalBlockBorderWrapper"] h2,
    [data-testid="stVerticalBlockBorderWrapper"] h3,
    [data-testid="stVerticalBlockBorderWrapper"] h4 {
        color: var(--champagne) !important;
    }
    [data-testid="stAlert"] {
        border: 1px solid var(--gold);
        border-radius: 1rem;
        background: rgba(243, 229, 171, 0.44);
    }
    [data-testid="stAlert"] p,
    [data-testid="stAlert"] [data-testid="stMarkdownContainer"] {
        color: var(--espresso) !important;
    }
    div.stButton > button, div.stFormSubmitButton > button {
        position: relative;
        overflow: hidden;
        background:
            linear-gradient(180deg, rgba(255, 255, 255, 0.42) 0%, rgba(255, 255, 255, 0) 48%),
            linear-gradient(180deg, var(--crimson) 0%, var(--cherry) 100%) !important;
        color: var(--parchment) !important;
        -webkit-text-fill-color: var(--parchment) !important;
        border: 2px solid var(--gold) !important;
        border-radius: 999px !important;
        min-height: 3.15rem;
        padding: 0.68rem 1.45rem;
        font-family: "Cormorant Garamond", "Palatino Linotype", Georgia, serif;
        font-size: 1.13rem;
        font-weight: 700;
        box-shadow: 0 8px 16px -2px rgba(43, 27, 23, 0.35), inset 0 -3px 6px rgba(0, 0, 0, 0.4);
        transition: transform 150ms ease, box-shadow 150ms ease, filter 150ms ease;
    }
    div.stButton > button::after, div.stFormSubmitButton > button::after {
        content: "";
        position: absolute;
        top: -60%;
        left: -35%;
        width: 34%;
        height: 220%;
        transform: rotate(28deg);
        background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.42), transparent);
        transition: left 450ms ease;
        pointer-events: none;
    }
    div.stButton > button:hover::after,
    div.stFormSubmitButton > button:hover::after { left: 115%; }
    div.stButton > button:hover, div.stFormSubmitButton > button:hover {
        color: #FFFFFF !important;
        border-color: var(--champagne) !important;
        filter: brightness(1.08);
        transform: translateY(-2px);
        box-shadow: 0 11px 20px -2px rgba(43, 27, 23, 0.38), inset 0 -3px 6px rgba(0, 0, 0, 0.35);
    }
    div.stButton > button:active, div.stFormSubmitButton > button:active {
        transform: scale(0.96) translateY(2px);
        box-shadow: 0 3px 7px rgba(43, 27, 23, 0.3), inset 0 -2px 5px rgba(0, 0, 0, 0.42);
    }
    .st-key-outline_clear_transcript button,
    .st-key-outline_clear_transcript_dim button,
    .st-key-outline_edit_checkin_top button,
    .st-key-outline_sign_out_top button {
        background: rgba(247, 242, 231, 0.75) !important;
        color: var(--cherry) !important;
        -webkit-text-fill-color: var(--cherry) !important;
        border: 1.5px solid var(--gold) !important;
        box-shadow: 0 3px 8px rgba(43, 27, 23, 0.12) !important;
        border-radius: 999px !important;
        min-height: 44px !important;
        white-space: nowrap !important;
    }
    /* Dimmed Clear keeps at least ~3:1 on parchment (wine-tint on cream). */
    .st-key-outline_clear_transcript_dim button {
        color: #7A4A52 !important;
        -webkit-text-fill-color: #7A4A52 !important;
        border-color: rgba(201, 162, 75, 0.65) !important;
        background: rgba(247, 242, 231, 0.45) !important;
        box-shadow: none !important;
    }
    .st-key-card_voice_transcript [data-testid="stHorizontalBlock"] {
        align-items: center;
        margin-bottom: 0.15rem;
    }
    .st-key-card_voice_transcript .transcript-empty {
        font-family: "Cormorant Garamond", "Palatino Linotype", Georgia, serif;
        font-style: italic;
        color: #F3E5AB;
        margin: 0.35rem 0 0.55rem;
    }
    .st-key-card_voice_transcript [data-testid="stTextArea"] textarea {
        font-family: "Cormorant Garamond", "Palatino Linotype", Georgia, serif !important;
        font-size: 1.05rem !important;
    }
    [data-testid="stSlider"] [data-baseweb="slider"] [role="slider"] {
        width: 32px !important;
        height: 32px !important;
        background:
            linear-gradient(180deg, rgba(255, 255, 255, 0.46), transparent 48%),
            linear-gradient(180deg, var(--crimson), var(--cherry)) !important;
        border: 3px solid var(--gold) !important;
        border-radius: 50% !important;
        box-shadow: 0 5px 12px rgba(43, 27, 23, 0.35), inset 0 -2px 4px rgba(0, 0, 0, 0.3) !important;
        transition: transform 120ms ease, box-shadow 120ms ease;
    }
    [data-testid="stSlider"] [data-baseweb="slider"] [role="slider"]:active {
        transform: scale(1.13);
        box-shadow: 0 2px 6px rgba(43, 27, 23, 0.3), inset 0 -2px 4px rgba(0, 0, 0, 0.35) !important;
    }
    [data-testid="stSlider"] [data-baseweb="slider"] [role="slider"]:focus {
        outline: 3px solid var(--gold) !important;
        outline-offset: 3px !important;
    }
    [data-baseweb="select"] > div,
    [data-baseweb="input"] > div,
    [data-testid="stNumberInput"] input,
    [data-testid="stDateInput"] input,
    [data-testid="stTextArea"] textarea,
    [data-testid="stTextInput"] input {
        background: #FFFCF5 !important;
        color: var(--espresso) !important;
        -webkit-text-fill-color: var(--espresso) !important;
        caret-color: var(--cherry) !important;
        border-color: rgba(139, 30, 38, 0.65) !important;
        border-radius: 0.8rem !important;
    }
    input, textarea { color: var(--espresso) !important; -webkit-text-fill-color: var(--espresso) !important; }
    [data-testid="stNumberInput"] button {
        color: var(--parchment) !important;
        -webkit-text-fill-color: var(--parchment) !important;
        background: linear-gradient(180deg, var(--crimson), var(--cherry)) !important;
        border: 1px solid var(--gold) !important;
        border-radius: 999px !important;
    }
    [data-testid="stExpander"] summary,
    [data-testid="stExpander"] summary p,
    [data-testid="stExpander"] summary span {
        color: var(--taupe) !important;
        -webkit-text-fill-color: var(--taupe) !important;
        font-weight: 700;
    }
    .st-key-card_voice_transcript {
        background: var(--mahogany) !important;
        border: 1.5px solid var(--gold);
        border-radius: 1.25rem;
        padding: 0.5rem 0.8rem;
        overflow: visible !important;
    }
    [data-testid="stTabs"] [role="tab"] {
        color: var(--taupe) !important;
        font-family: "Cormorant Garamond", "Palatino Linotype", Georgia, serif;
        font-size: 1.13rem;
    }
    [data-testid="stTabs"] [role="tab"][aria-selected="true"] {
        color: var(--cherry) !important;
        border-bottom-color: var(--gold) !important;
        font-weight: 750;
    }
    [data-testid="stCode"] pre {
        background: #FFFCF5 !important;
        color: var(--cherry) !important;
        border: 2px solid var(--gold) !important;
        border-radius: 1rem !important;
        font-size: 1.5rem !important;
        font-weight: 750 !important;
        letter-spacing: 0.14em !important;
        text-align: center !important;
        padding: 1rem !important;
    }
    .phase-wheel {
        width: min(220px, 70vw);
        aspect-ratio: 1;
        margin: 1rem auto 1.5rem;
        border-radius: 50%;
        display: grid;
        place-items: center;
        position: relative;
        box-shadow: 0 8px 22px rgba(43, 27, 23, 0.23), 0 0 0 5px rgba(212, 175, 55, 0.24);
    }
    .phase-wheel svg {
        position: absolute;
        inset: 0;
        width: 100%;
        height: 100%;
    }
    .phase-wheel-center {
        position: relative;
        z-index: 1;
        width: 58%;
        height: 58%;
        border-radius: 50%;
        background: radial-gradient(circle at 35% 25%, #FFFCF5, var(--parchment) 72%);
        border: 2px solid var(--gold);
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        color: var(--cherry);
        text-align: center;
        font-family: "Playfair Display", "Palatino Linotype", Georgia, serif;
        font-weight: 700;
        line-height: 1.25;
    }
    .phase-wheel-center small {
        color: var(--taupe);
        font-family: "Cormorant Garamond", "Palatino Linotype", Georgia, serif;
        font-size: 0.78rem;
        font-weight: 500;
    }
    .phase-legend {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 0.45rem 0.8rem;
        max-width: 390px;
        margin: 0 auto;
        color: var(--espresso);
        font-size: 1.05rem;
    }
    .phase-legend span.active { color: var(--cherry); font-weight: 750; }
    @media (max-width: 480px) {
        h1 { font-size: 2.25rem !important; }
        h2 { font-size: 1.8rem !important; }
        .phase-brand { margin-bottom: 1.4rem; padding-inline: 0.8rem; }
        div.stButton > button, div.stFormSubmitButton > button {
            min-height: 3rem;
            padding-inline: 1.05rem;
        }
    }
    /* Export PDF and primary download actions */
    div.stDownloadButton > button {
        background:
            linear-gradient(180deg, rgba(255, 255, 255, 0.38) 0%, rgba(255, 255, 255, 0) 48%),
            linear-gradient(180deg, var(--crimson) 0%, var(--cherry) 100%) !important;
        color: var(--parchment) !important;
        -webkit-text-fill-color: var(--parchment) !important;
        border: 2px solid var(--gold) !important;
        border-radius: 999px !important;
        min-height: 3.15rem;
        padding: 0.68rem 1.45rem;
        font-family: "Cormorant Garamond", "Palatino Linotype", Georgia, serif;
        font-size: 1.13rem;
        font-weight: 700;
        box-shadow: 0 8px 16px -2px rgba(43, 27, 23, 0.35), inset 0 -3px 6px rgba(0, 0, 0, 0.4);
        transition: transform 150ms ease, box-shadow 150ms ease, filter 150ms ease;
    }
    div.stDownloadButton > button:hover {
        color: #FFFFFF !important;
        border-color: var(--champagne) !important;
        filter: brightness(1.08);
        transform: translateY(-2px);
    }
    /* What might help controls */
    [data-testid="stSegmentedControl"] button {
        border-radius: 999px !important;
        border: 1.5px solid var(--gold) !important;
        color: #7A4A52 !important;
        -webkit-text-fill-color: #7A4A52 !important;
        background: rgba(243, 233, 210, 0.7) !important;
        font-weight: 700;
        font-size: 1rem !important;
        white-space: nowrap !important;
        min-width: 0 !important;
    }
    [data-testid="stSegmentedControl"] {
        gap: 0.35rem !important;
    }
    [data-testid="stSegmentedControl"] button[aria-checked="true"] {
        background: linear-gradient(180deg, var(--crimson), var(--cherry)) !important;
        color: var(--parchment) !important;
        -webkit-text-fill-color: var(--parchment) !important;
    }
    [data-testid="stSelectbox"] [data-baseweb="select"] {
        border-radius: 999px !important;
        border: 1.5px solid var(--gold) !important;
        background: rgba(243, 233, 210, 0.7) !important;
    }
    .luna-avatar {
        width: 56px;
        height: 56px;
        border-radius: 50%;
        border: 2px solid var(--gold);
        background:
            radial-gradient(circle at 30% 28%, rgba(255, 255, 255, 0.55), transparent 34%),
            radial-gradient(circle at 50% 50%, var(--champagne), var(--cherry));
        display: inline-flex;
        align-items: center;
        justify-content: center;
        box-shadow:
            0 0 0 6px rgba(201, 162, 75, 0.14),
            0 8px 18px rgba(43, 27, 23, 0.28);
        animation: luna-pulse 3.2s ease-in-out infinite;
    }
    .luna-avatar svg { display: block; }
    @keyframes luna-pulse {
        0%, 100% { transform: scale(1); box-shadow: 0 0 0 6px rgba(201, 162, 75, 0.14), 0 8px 18px rgba(43, 27, 23, 0.28); }
        50% { transform: scale(1.04); box-shadow: 0 0 0 9px rgba(201, 162, 75, 0.22), 0 10px 22px rgba(43, 27, 23, 0.34); }
    }
    @media (prefers-reduced-motion: reduce) {
        .luna-avatar { animation: none; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)
st.markdown(
    """
    <div class="phase-brand" aria-label="Cadence, a cycle-aware wellness guide">
      <div class="phase-brand-title">CADENCE</div>
      <div class="phase-brand-divider"><span>◇</span></div>
      <div class="phase-brand-subtitle">A cycle-aware guide, led by how you feel</div>
    </div>
    """,
    unsafe_allow_html=True,
)


@st.cache_resource
def connect_database(uri: str, database_name: str):
    client = MongoClient(uri, serverSelectionTimeoutMS=5000)
    client.admin.command("ping")
    database = client[database_name]
    database.checkins.create_index(
        [("account_id", 1), ("checkin_date", 1)], unique=True
    )
    database.phase_hearts.create_index(
        [("account_id", 1), ("phase", 1)],
        unique=True,
    )
    database.phase_locks.create_index(
        [("account_id", 1), ("phase", 1)], unique=True
    )
    database.model_weights.create_index(
        [("account_id", 1), ("model", 1)], unique=True
    )
    return database


def show_auth_page() -> None:
    st.title("Cadence")
    st.write("A cycle-aware plan that starts with how you feel today.")
    st.subheader("Your account")
    st.write(
        "No email, phone number, or password. Cadence creates a private 10-character "
        "code for sign-in. Save it somewhere safe; if it is lost, the account "
        "and its data cannot be recovered."
    )
    sign_in_tab, create_tab = st.tabs(("Sign in", "Create account"))

    with sign_in_tab:
        with st.form("sign-in-form"):
            code = st.text_input(
                "Your 10-character sign-in code",
                max_chars=12,
                type="password",
                help="This code is the only way to sign back in.",
            )
            submitted = st.form_submit_button("Sign in")
        if submitted:
            try:
                account = authenticate_account(
                    database.accounts,
                    code,
                )
            except PyMongoError:
                st.error("Account sign-in is temporarily unavailable. Try again.")
            except ValueError as error:
                st.error(str(error))
            else:
                if account is None:
                    st.error(
                        "That code was not found. Check it and try again. "
                        "Lost codes cannot be recovered."
                    )
                else:
                    st.session_state["account_id"] = account["_id"]
                    profile = account.get("profile")
                    st.session_state["flow_step"] = (
                        "profile"
                        if not isinstance(profile, dict)
                        or profile.get("version") != PROFILE_VERSION
                        else "checkin"
                    )
                    st.rerun()

    with create_tab:
        st.write("Create an account with no name, email, or phone number.")
        with st.form("create-account-form"):
            age_text = st.text_input("Age", value="18")
            privacy_acknowledged = st.checkbox(
                "I understand the sign-in code is shown once and cannot be recovered."
            )
            submitted = st.form_submit_button("Create my account")
        if submitted:
            try:
                age = int(age_text.strip())
            except ValueError:
                age = None
                st.error("Enter a whole number for age.")
            if age is not None:
                if age < 18:
                    st.error("Phase is for adults 18 and older.")
                elif not privacy_acknowledged:
                    st.error("Confirm that you understand how the sign-in code works.")
                else:
                    try:
                        account_id, login_code = create_account(
                            database.accounts,
                            age,
                        )
                    except PyMongoError:
                        st.error("Account storage is unavailable. Please try again later.")
                    else:
                        st.session_state["pending_login_code"] = login_code
                        st.session_state["account_id"] = account_id
                        st.rerun()


def show_recovery_code() -> None:
    st.title("Save your sign-in code")
    st.warning(
        "This is the only time Phase will show this code. It is not stored in "
        "readable form. If you lose it, your account cannot be recovered."
    )
    st.code(st.session_state["pending_login_code"], language=None)
    with st.form("save-code-confirmation"):
        saved = st.checkbox("I saved my code somewhere private.")
        submitted = st.form_submit_button("Continue to setup")
    if submitted:
        if not saved:
            st.error("Save the code before continuing.")
        else:
            st.session_state.pop("pending_login_code", None)
            st.session_state["flow_step"] = "profile"
            st.rerun()


def show_profile_setup(account) -> None:
    st.title("Set up your profile")
    st.write("These details shape your cycle estimate and training plan.")
    with st.form("profile-setup-form"):
        cycle_tracking_choice = st.selectbox(
            "Cycle tracking",
            TRACKING_MODES,
        )
        last_period = None
        date_confirmed = True
        if cycle_tracking_choice == TRACKING_MODES[0]:
            last_period = st.date_input(
                "Last period start",
                value=TODAY,
            )
            date_confirmed = st.checkbox("I confirmed this is the correct date")
        workouts_per_week = st.slider(
            "Workouts per week",
            min_value=1,
            max_value=7,
            value=3,
        )
        usual_split = st.selectbox("Usual training split", WORKOUT_SPLITS)
        goal = st.selectbox("Your goal", GOALS)
        submitted = st.form_submit_button("Save profile and continue")

    if submitted:
        cycle_tracking_mode = TRACKING_MODE_VALUES[cycle_tracking_choice]
        if cycle_tracking_mode == "period_date" and not date_confirmed:
            st.error("Confirm your last period date, or choose symptom-based mode.")
        elif last_period is not None and last_period > TODAY:
            st.error("Last period start cannot be in the future.")
        else:
            profile = stored_profile(
                {
                    "cycle_tracking_mode": cycle_tracking_mode,
                    "last_period": last_period,
                    "workouts_per_week": workouts_per_week,
                    "usual_split": usual_split,
                    "goal": goal,
                }
            )
            try:
                database.accounts.update_one(
                    {"_id": account["_id"]},
                    {
                        "$set": {
                            "profile": profile,
                            "updated_at": datetime.now(timezone.utc),
                        }
                    },
                )
            except PyMongoError:
                st.error(
                    "Could not save your profile to MongoDB. Please try again."
                )
                st.stop()
            st.session_state["flow_step"] = "checkin"
            st.rerun()


def show_voice_checkin() -> None:
    with st.expander("Voice check-in (record, then upload)", expanded=True):
        st.write(
            "Record up to 60 seconds. Say how your flow, mood, energy, sleep, "
            "pain, and workout are going."
        )
        st.caption(
            "Example: “I have light flow, feel low energy, slept five hours, "
            "have moderate cramps, and did not work out.”"
        )
        st.caption(
            "This is record-then-upload, not live transcription. Audio is sent "
            "to the local Phase API and is not saved in MongoDB. If microphone "
            "recording fails, upload an audio file or use the tap form below."
        )
        with st.container(border=True, key="card_voice_transcript"):
            # One header row: label left, Clear right, then body, then audio.
            # Clear must stay above the recorder (not in Streamlit chrome).
            has_transcript = bool(
                str(st.session_state.get("voice_transcript") or "").strip()
            )
            transcript_heading, clear_transcript = st.columns(
                (3, 1),
                vertical_alignment="center",
                gap="small",
            )
            # Honest label while record-then-upload is the only path (not live).
            transcript_heading.markdown("#### Transcript")
            clear_key = (
                "outline_clear_transcript"
                if has_transcript
                else "outline_clear_transcript_dim"
            )
            if clear_transcript.button("Clear ×", key=clear_key):
                discard_audio_capture()
                clear_voice_text()
                st.rerun()
            if has_transcript:
                st.text_area(
                    "Editable transcript",
                    key="voice_transcript",
                    height=120,
                    label_visibility="collapsed",
                    on_change=clean_voice_transcript,
                )
            else:
                st.markdown(
                    '<div style="display:flex;align-items:center;gap:0.65rem;margin:0.2rem 0 0.5rem;">'
                    '<span class="luna-avatar" aria-hidden="true" style="width:40px;height:40px;">'
                    '<svg viewBox="0 0 56 56" width="28" height="28" fill="none" xmlns="http://www.w3.org/2000/svg">'
                    '<defs><radialGradient id="luna-moon-small" cx="35%" cy="30%"><stop offset="0%" stop-color="#FFF7E6"/><stop offset="100%" stop-color="#C9A24B"/></radialGradient></defs>'
                    '<circle cx="28" cy="28" r="24" fill="url(#luna-moon-small)"/>'
                    '<path d="M34 14a16 16 0 1 0 0 28 13 13 0 0 1 0-28Z" fill="#F3E5AB" opacity="0.85"/>'
                    '<circle cx="20" cy="22" r="2.6" fill="#2B1B17"/>'
                    '<circle cx="32" cy="22" r="2.6" fill="#2B1B17"/>'
                    '<path d="M20 31c3 3.6 13 3.6 16 0" stroke="#2B1B17" stroke-width="2.2" stroke-linecap="round"/>'
                    '</svg></span>'
                    '<p class="transcript-empty" style="margin:0;">Luna is listening...</p></div>',
                    unsafe_allow_html=True,
                )
            # Streamlit 1.53.1 signature: audio_input(label, *, sample_rate=16000, key=None, help=None, on_change=None, args=None, kwargs=None, disabled=False, label_visibility="visible", width="stretch").
            with st.form("voice-checkin-form"):
                voice_audio = st.audio_input(
                    "Record your check-in",
                    sample_rate=16000,
                    key=f"audio_{int(st.session_state.get('audio_nonce', 0))}",
                    help="Your browser may ask for microphone access.",
                )
                uploaded_audio = st.file_uploader(
                    "Or upload an audio file",
                    type=("wav", "mp3", "m4a", "mp4", "webm", "ogg"),
                    key="voice-upload",
                )
                transcribe_voice = st.form_submit_button(
                    "Transcribe with Cartesia"
                )
        if transcribe_voice:
            audio = uploaded_audio if uploaded_audio is not None else voice_audio
            if audio is None:
                st.error(
                    "No recording was received. Check browser microphone "
                    "permissions, upload a recording, or use the tap form below."
                )
            else:
                audio_type = (
                    uploaded_audio.type
                    if uploaded_audio is not None
                    else "audio/wav"
                )
                request = Request(
                    "http://127.0.0.1:4000/api/cartesia/transcribe",
                    data=audio.getvalue(),
                    headers={"Content-Type": audio_type},
                    method="POST",
                )
                try:
                    with urlopen(request, timeout=45) as response:
                        payload = json.loads(response.read().decode("utf-8"))
                    transcript = payload.get("text")
                    if not isinstance(transcript, str) or not transcript.strip():
                        st.error(
                            "Cartesia returned an empty transcript. Try recording again."
                        )
                    else:
                        # Keep WAV in memory for G1 only; discard on Clear/save.
                        st.session_state["voice_wav_bytes"] = audio.getvalue()
                        st.session_state["voice_wav_type"] = audio_type
                        st.session_state["voice_transcript"] = strip_spoken_names(
                            strip_emojis(transcript)
                        )
                        st.session_state["voice_transcribed"] = True
                        discard_audio_capture()
                        st.rerun()
                except HTTPError as error:
                    try:
                        details = json.loads(error.read().decode("utf-8"))
                        message = details.get(
                            "error",
                            "Transcription request failed.",
                        )
                    except (UnicodeDecodeError, json.JSONDecodeError):
                        message = "Transcription request failed."
                    st.error(f"Cartesia transcription failed: {message}")
                except URLError:
                    st.error(
                        "Could not reach the local Phase API at port 4000. "
                        "Start the API in a separate terminal and try again."
                    )
                except (TimeoutError, json.JSONDecodeError):
                    st.error(
                        "The transcription request timed out or returned invalid JSON."
                    )

        if "voice_transcript" in st.session_state:
            if st.session_state.pop("voice_transcribed", False):
                st.success(
                    "Review and correct the transcript before extracting "
                    "check-in values."
                )
            st.caption(
                "Remove your name or identifying details before extraction. "
                "The transcript is temporary and is not saved to your account."
            )
            if st.button(
                "Extract check-in values",
                key="extract-voice-fields",
            ):
                transcript = strip_spoken_names(
                    strip_emojis(st.session_state["voice_transcript"])
                ).strip()
                if not transcript:
                    st.error("Enter or correct the transcript before extraction.")
                else:
                    wav_bytes = st.session_state.get("voice_wav_bytes")
                    wav_type = st.session_state.get("voice_wav_type", "audio/wav")
                    try:
                        if isinstance(wav_bytes, (bytes, bytearray)) and wav_bytes:
                            # G1 multimodal path: audio + helper transcript.
                            request = Request(
                                "http://127.0.0.1:4000/api/gemini/checkin-audio",
                                data=bytes(wav_bytes),
                                headers={
                                    "Content-Type": str(wav_type),
                                    "X-Phase-Transcript": transcript[:4000],
                                },
                                method="POST",
                            )
                        else:
                            request = Request(
                                "http://127.0.0.1:4000/api/gemini/checkin",
                                data=json.dumps(
                                    {"transcript": transcript}
                                ).encode("utf-8"),
                                headers={"Content-Type": "application/json"},
                                method="POST",
                            )
                        with urlopen(request, timeout=45) as response:
                            payload = json.loads(response.read().decode("utf-8"))
                        fields = payload.get("fields")
                        if not isinstance(fields, dict):
                            raise ValueError("Gemini returned invalid check-in fields.")
                        st.session_state["voice_extracted"] = fields
                        st.session_state["voice_g1_result"] = fields
                        st.session_state["voice_field_provenance"] = {
                            key: "Heard in your voice"
                            for key, value in fields.items()
                            if value is not None
                        }
                        input_keys = {
                            "flow": "checkin-flow",
                            "mood": "checkin-mood",
                            "energy": "checkin-energy",
                            "sleep_hours": "checkin-sleep",
                            "pain": "checkin-pain",
                            "workout_done": "checkin-workout-done",
                            "severe_pain": "checkin-severe-pain",
                            "persistently_irregular_cycles": "checkin-irregular",
                            "positive_pregnancy_test": "checkin-pregnancy",
                        }
                        for field, key in input_keys.items():
                            if fields.get(field) is not None:
                                st.session_state[key] = fields[field]
                        st.success(
                            "Review the suggested values in the tap form and correct "
                            "anything that does not match how you feel. "
                            "Heard fields are tagged until you confirm them."
                        )
                        st.rerun()
                    except HTTPError as error:
                        try:
                            details = json.loads(error.read().decode("utf-8"))
                            message = details.get(
                                "error",
                                "Extraction request failed.",
                            )
                        except (UnicodeDecodeError, json.JSONDecodeError):
                            message = "Extraction request failed."
                        st.error(f"Gemini extraction failed: {message}")
                    except (URLError, TimeoutError):
                        st.error(
                            "Could not reach the local Phase API. Check that it is "
                            "running, then use the tap form if needed."
                        )
                    except (json.JSONDecodeError, ValueError) as error:
                        st.error(f"Could not use the extracted values: {error}")


def show_daily_checkin(account) -> None:
    st.title("How are you feeling today?")
    st.write(
        "Your check-in leads. Cycle phase is only a starting estimate."
    )
    try:
        existing = get_checkin(database.checkins, account["_id"], TODAY) or {}
    except PyMongoError:
        st.error("Could not load today's check-in from MongoDB. Please reload.")
        st.stop()
    show_voice_checkin()
    suggested = st.session_state.get("voice_extracted", {})
    suggested_flow = suggested.get("flow")
    if suggested_flow not in FLOWS:
        suggested_flow = existing.get("flow", "None")
    suggested_mood = suggested.get("mood")
    if suggested_mood not in MOODS:
        suggested_mood = existing.get("mood", "Okay")
    if "voice_extracted" in st.session_state:
        st.info(
            "Review and correct every voice suggestion before continuing."
        )

    initial_values = {
        "checkin-flow": suggested_flow,
        "checkin-mood": suggested_mood,
        "checkin-energy": int(
            suggested.get("energy")
            if suggested.get("energy") in range(1, 6)
            else existing.get("energy", 3)
        ),
        "checkin-sleep": float(
            suggested.get("sleep_hours")
            if isinstance(suggested.get("sleep_hours"), (int, float))
            and 0 <= suggested["sleep_hours"] <= 12
            else existing.get("sleep_hours", 7.0)
        ),
        "checkin-pain": int(
            suggested.get("pain")
            if suggested.get("pain") in range(0, 11)
            else existing.get("pain", 0)
        ),
        "checkin-workout-done": bool(
            suggested.get("workout_done")
            if isinstance(suggested.get("workout_done"), bool)
            else existing.get("workout_done", False)
        ),
        "checkin-severe-pain": bool(
            suggested.get("severe_pain")
            if isinstance(suggested.get("severe_pain"), bool)
            else existing.get("severe_pain", False)
        ),
        "checkin-irregular": bool(
            suggested.get("persistently_irregular_cycles")
            if isinstance(
                suggested.get("persistently_irregular_cycles"),
                bool,
            )
            else existing.get("persistently_irregular_cycles", False)
        ),
        "checkin-pregnancy": bool(
            suggested.get("positive_pregnancy_test")
            if isinstance(suggested.get("positive_pregnancy_test"), bool)
            else existing.get("positive_pregnancy_test", False)
        ),
    }
    for key, value in initial_values.items():
        if key not in st.session_state:
            st.session_state[key] = value

    with st.form("daily-checkin-form"):
        flow = st.selectbox(
            "Flow",
            FLOWS,
            key="checkin-flow",
        )
        provenance = st.session_state.get("voice_field_provenance") or {}
        mood = st.selectbox(
            "Mood",
            MOODS,
            key="checkin-mood",
            help=provenance.get("mood"),
        )
        energy = st.slider(
            "Energy",
            min_value=1,
            max_value=5,
            key="checkin-energy",
            help=provenance.get("energy"),
        )
        sleep = st.slider(
            "Sleep (hours)",
            min_value=0.0,
            max_value=12.0,
            step=0.5,
            key="checkin-sleep",
            help=provenance.get("sleep_hours"),
        )
        pain = st.slider(
            "Pain (0 to 10)",
            min_value=0,
            max_value=10,
            key="checkin-pain",
            help=provenance.get("pain"),
        )
        if provenance:
            st.caption(
                "Fields marked Heard in your voice came from your recording. "
                "Edit anything that is wrong before continuing."
            )
        workout_done = st.checkbox(
            "I completed a workout",
            key="checkin-workout-done",
        )
        severe_pain = st.checkbox(
            "My pain feels severe",
            key="checkin-severe-pain",
        )
        irregular = st.checkbox(
            "My cycles are persistently under 21 or over 35 days",
            key="checkin-irregular",
        )
        pregnancy = st.checkbox(
            "I had a positive pregnancy test",
            key="checkin-pregnancy",
        )
        submitted = st.form_submit_button("Continue to my dashboard")

    if submitted:
        values = {
            "flow": flow,
            "mood": mood,
            "energy": energy,
            "sleep_hours": sleep,
            "pain": pain,
            "workout_done": workout_done,
            "severe_pain": severe_pain,
            "irregular": irregular,
            "pregnancy": pregnancy,
        }
        try:
            save_checkin(database.checkins, account["_id"], values, TODAY)
        except PyMongoError:
            st.error(
                "Could not save today's check-in to MongoDB. "
                "Your answers were not saved; please try again."
            )
            st.stop()
        # G2 readback text, then Sonic (3s). On failure, keep text only.
        summary = (
            f"Mood {mood}, energy {energy} of 5, sleep {sleep:g} hours, "
            f"pain {pain} of 10, flow {flow}."
        )
        readback_text = (
            f"Got it. Mood {mood}, energy {energy} of 5, "
            f"about {sleep:g} hours of sleep."
        )
        try:
            g2_request = Request(
                "http://127.0.0.1:4000/api/gemini/readback",
                data=json.dumps({"summary": summary}).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urlopen(g2_request, timeout=8) as response:
                g2_payload = json.loads(response.read().decode("utf-8"))
            candidate = g2_payload.get("readback")
            if isinstance(candidate, str) and candidate.strip():
                readback_text = strip_emojis(candidate.strip())
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError):
            pass
        st.session_state["voice_readback_text"] = readback_text
        try:
            tts_request = Request(
                "http://127.0.0.1:4000/api/cartesia/readback",
                data=json.dumps({"transcript": readback_text}).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urlopen(tts_request, timeout=3.5) as response:
                st.session_state["voice_readback_audio"] = response.read()
        except (HTTPError, URLError, TimeoutError):
            st.session_state.pop("voice_readback_audio", None)
        clear_voice_text()
        discard_audio_capture()
        discard_g1_audio()
        st.session_state["_clear_checkin_state"] = True
        st.session_state["flow_step"] = "dashboard"
        st.rerun()


def phase_wheel(phase: str | None, cycle_day: int | None = None, cycle_length: float | None = None) -> None:
    estimated_length = int(round(cycle_length)) if cycle_length else 28
    if estimated_length < 15:
        estimated_length = 28
    if cycle_day is None:
        progress = 0.0
    else:
        progress = min(max(cycle_day / estimated_length, 0.0), 1.0)
    circumference = 2 * 3.14159265 * 84
    dash = progress * circumference
    gap = circumference - dash
    center = phase or "No phase"
    if cycle_day is not None:
        subtitle = f"Day {cycle_day} of {estimated_length}"
    else:
        subtitle = "symptom guidance"
    description = (
        f"{phase} is highlighted on day {cycle_day} of an estimated "
        f"{estimated_length}-day cycle."
        if phase and cycle_day is not None
        else ("No cycle phase is estimated." if phase is None else f"{phase} is highlighted.")
    )
    st.markdown(
        f"""
        <div class="phase-wheel" role="img" aria-label="{description}">
          <svg viewBox="0 0 200 200" width="100%" height="100%">
            <circle cx="100" cy="100" r="84" fill="none" stroke="#E8DDC9" stroke-width="14"/>
            <circle cx="100" cy="100" r="84" fill="none" stroke="#9B1B30" stroke-width="14"
                    stroke-linecap="round"
                    stroke-dasharray="{dash:.1f} {gap:.1f}"
                    transform="rotate(-90 100 100)"/>
            <circle cx="100" cy="100" r="62" fill="#F3E9D2" stroke="#C9A24B" stroke-width="2"/>
          </svg>
          <div class="phase-wheel-center">{center}<small>{subtitle}</small></div>
        </div>
        <div class="phase-legend">
          {''.join(f'<span class="{"active" if phase == name else ""}">{name}</span>' for name in PHASES)}
        </div>
        """,
        unsafe_allow_html=True,
    )
    if cycle_day is not None:
        st.caption(
            f"Day {cycle_day} of an estimated {estimated_length}-day cycle. "
            "This is an orientation view, not a time-scale or fertility chart."
        )
    else:
        st.caption(
            "Cycle timing is not estimated in symptom-based mode."
        )


def show_dashboard(account, profile: dict, checkin: dict) -> None:
    unsure = profile.get("cycle_date_unsure", False)
    tracking_mode = profile.get(
        "cycle_tracking_mode",
        "unsure" if unsure else "period_date",
    )
    last_period_raw = profile.get("last_period_start")
    last_period = (
        date.fromisoformat(last_period_raw)
        if last_period_raw and tracking_mode == "period_date"
        else None
    )
    try:
        history = list_checkins(database.checkins, account["_id"])
    except PyMongoError:
        history = []
    readiness_weights = None
    try:
        readiness_weights = get_readiness_weights(
            database.model_weights,
            account["_id"],
        )
    except PyMongoError:
        readiness_weights = None
    if readiness_weights is None:
        readiness_weights = default_readiness_weights()

    cycle_state = build_cycle_model(
        history,
        today=TODAY,
        tracking_mode=tracking_mode,
        last_period_start=last_period,
    )
    prediction = predict_cycle(
        today=TODAY,
        last_period_start=last_period,
        unsure=tracking_mode != "period_date",
        checkins=history,
        tracking_mode=tracking_mode,
    )
    safety = evaluate_safety(
        today=TODAY,
        last_period_start=last_period,
        flow=checkin["flow"],
        pain=checkin["pain"],
        severe_pain=checkin["severe_pain"],
        persistently_irregular_cycles=checkin["persistently_irregular_cycles"],
        positive_pregnancy_test=checkin["positive_pregnancy_test"],
        checkins=history,
        cycle_lengths=cycle_state.valid_cycle_lengths,
    )

    edit_checkin_col, sign_out_col = st.columns((1, 1))
    if edit_checkin_col.button(
        "Edit today's check-in",
        key="outline_edit_checkin_top",
    ):
        st.session_state["flow_step"] = "checkin"
        st.rerun()
    if sign_out_col.button("Sign out", key="outline_sign_out_top"):
        clear_voice_text()
        discard_audio_capture()
        for key in (
            "account_id",
            "flow_step",
            *CHECKIN_INPUT_KEYS,
        ):
            st.session_state.pop(key, None)
        st.rerun()

    st.title("Your Cadence dashboard")
    st.caption("Your reported state leads today's plan.")
    readback_text = st.session_state.get("voice_readback_text")
    if isinstance(readback_text, str) and readback_text.strip():
        with st.container(border=True, key="card_luna_readback"):
            st.markdown(
                '<div style="display:flex;align-items:center;gap:0.75rem;margin-bottom:0.35rem;">'
                '<span class="luna-avatar" aria-hidden="true">'
                '<svg viewBox="0 0 56 56" width="40" height="40" fill="none" xmlns="http://www.w3.org/2000/svg">'
                '<defs><radialGradient id="luna-moon" cx="35%" cy="30%"><stop offset="0%" stop-color="#FFF7E6"/><stop offset="100%" stop-color="#C9A24B"/></radialGradient></defs>'
                '<circle cx="28" cy="28" r="24" fill="url(#luna-moon)"/>'
                '<path d="M34 14a16 16 0 1 0 0 28 13 13 0 0 1 0-28Z" fill="#F3E5AB" opacity="0.85"/>'
                '<circle cx="20" cy="22" r="2.6" fill="#2B1B17"/>'
                '<circle cx="32" cy="22" r="2.6" fill="#2B1B17"/>'
                '<path d="M20 31c3 3.6 13 3.6 16 0" stroke="#2B1B17" stroke-width="2.2" stroke-linecap="round"/>'
                '</svg></span>'
                '<strong>Luna</strong></div>',
                unsafe_allow_html=True,
            )
            st.write(readback_text)
            audio_bytes = st.session_state.get("voice_readback_audio")
            if isinstance(audio_bytes, (bytes, bytearray)) and audio_bytes:
                st.audio(bytes(audio_bytes), format="audio/mp3")
    weekly_schedule = None
    locked_plan = None
    if not safety.suppress_plan:
        weekly_schedule = weekly_workout_schedule(
            phase=prediction.phase,
            goal=profile["goal"],
            workouts_per_week=profile["workouts_per_week"],
            usual_split=profile["usual_split"],
            energy=checkin["energy"],
            sleep_hours=checkin["sleep_hours"],
            pain=checkin["pain"],
            today=TODAY,
            mood=checkin.get("mood", "Okay"),
            readiness_weights=readiness_weights,
        )
        if prediction.phase:
            locked_plan = get_phase_lock(
                database.phase_locks,
                account["_id"],
                prediction.phase,
            )

    today_tab, workout_tab, help_tab, report_tab = st.tabs(
        ("Today", "Train", "What might help", "Report")
    )

    with today_tab:
        with st.container(border=True):
            st.subheader("Where you are")
            if prediction.phase is None:
                st.caption("Cycle timing is hidden in symptom-based mode.")
                st.info(prediction.reason)
            else:
                phase_wheel(
                    prediction.phase,
                    cycle_day=prediction.cycle_day,
                    cycle_length=prediction.predicted_length,
                )
                st.subheader(f"Estimated phase: {prediction.phase}")
                if prediction.population_default:
                    st.caption("Estimated from typical cycles.")
                st.write(prediction.reason)
        with st.container(border=True):
            st.markdown("#### Today's check-in")
            st.write(
                f"Mood: {checkin['mood']}  |  Energy: {checkin['energy']}/5  |  "
                f"Sleep: {checkin['sleep_hours']:g} hours  |  "
                f"Pain: {checkin['pain']}/10"
            )
        if safety.alerts:
            st.error(
                "Please consider contacting a clinician. Plans are suppressed "
                "for this check-in."
            )
            for alert in safety.alerts:
                st.write(f"- {alert}")
        st.button(
            "Update how I feel",
            on_click=lambda: st.session_state.update({"flow_step": "checkin"}),
        )

    with workout_tab:
        st.subheader("Your training week")
        if safety.suppress_plan:
            st.info("A training plan is not shown while an escalation is active.")
        else:
            display_schedule = (
                locked_plan.get("workout_plan")
                if locked_plan
                else weekly_schedule
            )
            if not isinstance(display_schedule, list):
                display_schedule = weekly_schedule
            if locked_plan:
                st.success(f"Your {prediction.phase}-keyed plan is locked.")
            for item in display_schedule:
                with st.container(border=True):
                    heading = f"{item['day']} - {item['title']}"
                    st.markdown(f"### {heading}")
                    if item.get("is_today"):
                        st.caption("Today, adjusted using your check-in.")
                    if item["type"] == "rest":
                        st.write(item["reps"])
                    else:
                        st.write(
                            f"{', '.join(item['exercises'])} · {item['sets']} "
                            f"sets · {item['reps']}."
                        )
            if prediction.phase:
                if not locked_plan:
                    if st.button("Heart this workout", key="heart-workout"):
                        add_phase_heart(
                            database.phase_hearts,
                            account["_id"],
                            prediction.phase,
                        )
                        save_phase_workout_plan(
                            database.phase_locks,
                            account["_id"],
                            prediction.phase,
                            weekly_schedule,
                        )
                        st.rerun()
                    total_hearts = count_phase_hearts(
                        database.phase_hearts,
                        account["_id"],
                    )
                    st.caption(
                        f"{total_hearts} of 4 phase hearts saved."
                    )
                    if total_hearts >= 4 and st.button(
                        "Lock my 4-week plan",
                        key="lock-workout-plan",
                    ):
                        lock_phase_plan(database.phase_locks, account["_id"])
                        st.rerun()

    with help_tab:
        st.subheader("What might help")
        symptom_mode = prediction.symptom_mode
        phase_value = prediction.phase
        if symptom_mode:
            st.caption("All days")
        else:
            st.caption(f"Phase: {phase_value or 'All days'}")
        lens = st.segmented_control(
            "Lens", options=list(LENSES), default="Medicine", key="help-lens"
        ) or "Medicine"
        symptom = st.selectbox("Symptom", options=list(SYMPTOMS), key="help-symptom")
        entries = filter_help(
            phase=phase_value,
            lens=lens,
            symptom=symptom,
            symptom_mode=symptom_mode,
        )
        if not entries:
            st.caption("No sourced guidance matches this selection.")
        for entry in entries:
            with st.container(border=True):
                st.markdown(f"### {entry.title}")
                st.write(entry.body)
                st.caption(f"Evidence: {entry.evidence}")

    with report_tab:
        st.subheader("Appointment report")
        checkins = list_checkins(database.checkins, account["_id"])
        stats = compute_cycle_stats(checkins, today=TODAY)
        with st.container(border=True):
            st.markdown("### Cadence summary")
            if True:
                st.caption("Synthetic demo data")
            cols = st.columns(2)
            cols[0].metric("Cycles logged", stats.cycles_logged)
            cols[1].metric("Mean", format_stat(stats.mean))
            cols = st.columns(2)
            cols[0].metric("Median", format_stat(stats.median))
            cols[1].metric("Mode", format_stat(stats.mode))
            cols = st.columns(2)
            cols[0].metric("Range", format_stat(stats.range_span))
            cols[1].metric("Standard deviation", format_stat(stats.stdev))
            if stats.bar_counts:
                st.caption("Cycle lengths: " + ", ".join(
                    f"{length}d x{count}" for length, count in stats.bar_counts
                ))
            if stats.flags:
                st.caption("Flags: " + "; ".join(stats.flags))
        pdf = build_report_pdf_bytes(stats, synthetic=True)
        st.download_button(
            "Export PDF",
            data=pdf,
            file_name="cadence-report.pdf",
            mime="application/pdf",
        )
        with st.container(border=True):
            st.markdown("### Partner brief")
            st.caption("Preview and share")
            st.write("No identifiers are included in the partner brief.")


if "pending_login_code" in st.session_state:
    show_recovery_code()
    st.stop()

mongo_uri = os.getenv("MONGODB_URI", "").strip()
database_name = (os.getenv("MONGODB_DATABASE") or "phase").strip() or "phase"
if not mongo_uri:
    st.warning(
        "Data storage: without a database connection, your account, check-ins, and "
        "phase hearts stay in this session and reset when the app restarts. "
        "To keep them, set MONGODB_URI in apps/web/.env."
    )
    database = connect_in_memory_cached(database_name)
    if database is None:
        st.title("Cadence")
        st.error("In-memory store is unavailable.")
        st.stop()
else:
    try:
        database = connect_database(mongo_uri, database_name)
    except PyMongoError:
        st.title("Cadence")
        st.error(
            "Could not connect to MongoDB. Check the connection string, database "
            "network access, and credentials in apps/web/.env. No account data was "
            "loaded."
        )
        st.stop()

if "account_id" not in st.session_state:
    show_auth_page()
    st.stop()

try:
    account = database.accounts.find_one({"_id": st.session_state["account_id"]})
except PyMongoError:
    st.error("Could not load your account from MongoDB. Please reload.")
    st.stop()
if account is None:
    st.session_state.pop("account_id", None)
    st.error("This account is unavailable. Sign in again.")
    st.stop()

profile = account.get("profile")
if (
    not isinstance(profile, dict)
    or profile.get("version") != PROFILE_VERSION
    or st.session_state.get("flow_step") == "profile"
):
    show_profile_setup(account)
    st.stop()

if st.session_state.pop("_clear_checkin_state", False):
    for key in CHECKIN_INPUT_KEYS:
        st.session_state.pop(key, None)

if st.session_state.get("flow_step") != "dashboard":
    show_daily_checkin(account)
    st.stop()

try:
    today_checkin = get_checkin(database.checkins, account["_id"], TODAY)
except PyMongoError:
    st.error("Could not load today's check-in from MongoDB. Please reload.")
    st.stop()
if today_checkin is None:
    st.session_state["flow_step"] = "checkin"
    st.rerun()
show_dashboard(account, profile, today_checkin)
