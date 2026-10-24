import json
import os
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import streamlit as st
from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.errors import PyMongoError

from persistence import (
    add_phase_heart,
    authenticate_account,
    create_account,
    count_phase_hearts,
    get_checkin,
    get_phase_lock,
    lock_phase_plan,
    save_checkin,
    stored_profile,
)
from phase_engine import build_plan, evaluate_safety, grocery_list, predict_cycle


load_dotenv(Path(__file__).with_name(".env"))
TODAY = date.today()
PHASES = ("Menstrual", "Follicular", "Ovulatory", "Luteal")
GOALS = ("Strength", "General fitness", "Energy")
EXERCISES = (
    "Bodyweight squat",
    "Glute bridge",
    "Wall push-up",
    "Dumbbell row",
    "Dead bug",
    "Step-up",
    "Hip hinge",
    "Overhead press",
)
DIETS = ("No preference", "Vegetarian", "Vegan", "Gluten-free")
FLOWS = ("None", "Spotting", "Light", "Moderate", "Heavy", "Very heavy")
MOODS = ("Low", "Okay", "Good", "Anxious", "Irritable")


st.set_page_config(page_title="Phase", page_icon=None, layout="centered")
st.markdown(
    """
    <style>
    :root { color-scheme: light; }
    .stApp, [data-testid="stAppViewContainer"], [data-testid="stSidebar"] {
        background: #F3E9D2;
        color: #2A1A14 !important;
    }
    .stApp, .stApp p, .stApp label, .stApp li,
    .stApp [data-testid="stMarkdownContainer"],
    .stApp [data-testid="stWidgetLabel"],
    .stApp [data-testid="stCaptionContainer"],
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] label {
        color: #2A1A14 !important;
        font-size: 1.05rem;
        line-height: 1.55;
    }
    h1, h2, h3 {
        color: #5A0F1C !important;
        font-family: Georgia, serif;
        letter-spacing: 0.01em;
    }
    h1 { font-size: 3rem !important; }
    h2 { font-size: 2.15rem !important; }
    h3 { font-size: 1.65rem !important; }
    [data-testid="stWidgetLabel"] p { font-weight: 650 !important; }
    [data-testid="stCaptionContainer"] p { font-size: 0.96rem !important; }
    [data-testid="stAlert"] {
        border: 1px solid #9B1B30;
        border-radius: 16px;
    }
    [data-testid="stAlert"] p,
    [data-testid="stAlert"] [data-testid="stMarkdownContainer"] {
        color: #2A1A14 !important;
    }
    div.stButton > button, div.stFormSubmitButton > button {
        background: #9B1B30 !important;
        color: #F3E9D2 !important;
        border: 1px solid #C9A24B;
        border-radius: 999px;
        min-height: 3rem;
        padding: 0.65rem 1.3rem;
        font-size: 1.02rem;
        font-weight: 650;
        box-shadow: 0 4px 12px rgba(42, 26, 20, 0.16);
        transition: transform 120ms ease, box-shadow 120ms ease;
    }
    div.stButton > button:hover, div.stFormSubmitButton > button:hover {
        background: #5A0F1C !important;
        color: #F3E9D2 !important;
        border-color: #C9A24B;
        transform: translateY(-1px);
        box-shadow: 0 6px 16px rgba(42, 26, 20, 0.22);
    }
    [data-testid="stSlider"] [data-baseweb="slider"] [role="slider"] {
        width: 30px !important;
        height: 30px !important;
        background: #9B1B30 !important;
        border: 3px solid #C9A24B !important;
        border-radius: 50% !important;
        box-shadow: 0 3px 9px rgba(42, 26, 20, 0.25) !important;
    }
    [data-testid="stSlider"] [data-baseweb="slider"] [role="slider"]:focus {
        outline: 3px solid #C9A24B !important;
        outline-offset: 3px !important;
    }
    [data-baseweb="select"] > div,
    [data-baseweb="input"] > div,
    [data-testid="stDateInput"] input,
    [data-testid="stTextArea"] textarea {
        background: #FFF9EE !important;
        color: #2A1A14 !important;
        border-color: #9B1B30 !important;
        border-radius: 12px !important;
    }
    [data-testid="stAudioInput"] button {
        border-radius: 999px !important;
        border: 2px solid #C9A24B !important;
        color: #F3E9D2 !important;
        background: #9B1B30 !important;
    }
    .phase-wheel {
        width: 220px;
        height: 220px;
        margin: 1rem auto 1.5rem;
        border-radius: 50%;
        display: grid;
        place-items: center;
        box-shadow: 0 8px 22px rgba(42, 26, 20, 0.18);
    }
    .phase-wheel-center {
        width: 126px;
        height: 126px;
        border-radius: 50%;
        background: #F3E9D2;
        border: 2px solid #C9A24B;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        color: #5A0F1C;
        text-align: center;
        font-weight: 700;
        line-height: 1.25;
    }
    .phase-wheel-center small {
        color: #2A1A14;
        font-size: 0.78rem;
        font-weight: 500;
    }
    .phase-legend {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 0.45rem 0.8rem;
        max-width: 390px;
        margin: 0 auto;
        color: #2A1A14;
        font-size: 0.98rem;
    }
    .phase-legend span.active { color: #9B1B30; font-weight: 750; }
    </style>
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
    database.hearts.create_index(
        [
            ("account_id", 1),
            ("phase", 1),
            ("plan_kind", 1),
            ("week", 1),
        ],
        unique=True,
    )
    database.phase_locks.create_index(
        [("account_id", 1), ("phase", 1)], unique=True
    )
    return database


def show_auth_page() -> None:
    st.title("Phase")
    st.write("A cycle-aware plan that starts with how you feel today.")
    st.caption("Informational, not a diagnosis.")
    st.subheader("Your account")
    st.write(
        "No email, phone number, or password. Phase creates a private 10-character "
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
                    st.session_state["flow_step"] = (
                        "profile" if account.get("profile") is None else "checkin"
                    )
                    st.rerun()

    with create_tab:
        st.write("Create an account with no name, email, or phone number.")
        with st.form("create-account-form"):
            age = st.number_input("Age", min_value=0, max_value=120, value=18)
            privacy_acknowledged = st.checkbox(
                "I understand the sign-in code is shown once and cannot be recovered."
            )
            submitted = st.form_submit_button("Create my account")
        if submitted:
            if age < 18:
                st.error("Phase is for adults 18 and older.")
            elif not privacy_acknowledged:
                st.error("Confirm that you understand how the sign-in code works.")
            else:
                try:
                    account_id, login_code = create_account(
                        database.accounts,
                        int(age),
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
    st.write("These details personalize estimates and plans. No identity details.")
    with st.form("profile-setup-form"):
        unsure = st.checkbox("I am unsure of my last period start")
        last_period = st.date_input(
            "Last period start",
            value=TODAY,
            disabled=unsure,
            help="If you are unsure, choose that option to avoid phase claims.",
        )
        date_confirmed = st.checkbox(
            "I confirmed this is the correct date",
            disabled=unsure,
        )
        knows_cycle_length = st.checkbox("I know my typical cycle length")
        cycle_length = None
        if knows_cycle_length:
            cycle_length = st.number_input(
                "Typical cycle length in days",
                min_value=21,
                max_value=35,
                value=28,
            )
        goal = st.selectbox("Your goal", GOALS)
        exercises = st.multiselect(
            "Exercises you currently do (up to 5)",
            EXERCISES,
            max_selections=5,
        )
        diet = st.selectbox("Dietary preference", DIETS)
        submitted = st.form_submit_button("Save profile and continue")

    if submitted:
        if not unsure and not date_confirmed:
            st.error("Confirm your last period date, or choose that you are unsure.")
        elif not unsure and last_period > TODAY:
            st.error("Last period start cannot be in the future.")
        else:
            profile = stored_profile(
                {
                    "unsure": unsure,
                    "last_period": last_period,
                    "cycle_length": (
                        int(cycle_length) if cycle_length is not None else None
                    ),
                    "goal": goal,
                    "exercises": exercises,
                    "diet": diet,
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
                st.error("Could not save your profile to MongoDB. Please try again.")
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
            "to the local Phase API and is not saved in MongoDB. If recording "
            "does not work in this browser, use the tap form below."
        )
        with st.form("voice-checkin-form"):
            voice_audio = st.audio_input(
                "Record your check-in",
                sample_rate=16000,
                help="Your browser may ask for microphone access.",
            )
            transcribe_voice = st.form_submit_button("Transcribe with Cartesia")
        if transcribe_voice:
            if voice_audio is None:
                st.error(
                    "No recording was received. Check browser microphone "
                    "permissions or use the tap form below."
                )
            else:
                request = Request(
                    "http://127.0.0.1:4000/api/cartesia/transcribe",
                    data=voice_audio.getvalue(),
                    headers={"Content-Type": "audio/wav"},
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
                        st.session_state["voice_transcript"] = transcript
                        st.success(
                            "Review the editable transcript, then enter or correct "
                            "the structured values below."
                        )
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
            st.text_area(
                "Editable transcript",
                key="voice_transcript",
                height=120,
            )
            st.caption(
                "Transcript extraction into check-in fields is not connected yet. "
                "Use the tap form to confirm each value."
            )


def show_daily_checkin(account) -> None:
    st.title("How are you feeling today?")
    st.write(
        "Your check-in leads. Cycle phase is only a starting estimate."
    )
    st.caption("Informational, not a diagnosis.")
    try:
        existing = get_checkin(database.checkins, account["_id"], TODAY) or {}
    except PyMongoError:
        st.error("Could not load today's check-in from MongoDB. Please reload.")
        st.stop()
    show_voice_checkin()

    with st.form("daily-checkin-form"):
        flow = st.selectbox(
            "Flow",
            FLOWS,
            index=FLOWS.index(existing.get("flow", "None")),
        )
        mood = st.selectbox(
            "Mood",
            MOODS,
            index=MOODS.index(existing.get("mood", "Okay")),
        )
        energy = st.slider(
            "Energy",
            min_value=1,
            max_value=5,
            value=int(existing.get("energy", 3)),
        )
        sleep = st.slider(
            "Sleep (hours)",
            min_value=0.0,
            max_value=12.0,
            step=0.5,
            value=float(existing.get("sleep_hours", 7.0)),
        )
        pain = st.slider(
            "Pain (0 to 10)",
            min_value=0,
            max_value=10,
            value=int(existing.get("pain", 0)),
        )
        workout_done = st.checkbox(
            "I completed a workout",
            value=bool(existing.get("workout_done", False)),
        )
        severe_pain = st.checkbox(
            "My pain feels severe",
            value=bool(existing.get("severe_pain", False)),
        )
        irregular = st.checkbox(
            "My cycles are persistently under 21 or over 35 days",
            value=bool(existing.get("persistently_irregular_cycles", False)),
        )
        pregnancy = st.checkbox(
            "I had a positive pregnancy test",
            value=bool(existing.get("positive_pregnancy_test", False)),
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
        st.session_state["flow_step"] = "dashboard"
        st.rerun()


def phase_wheel(phase: str | None) -> None:
    colors = ("#9B1B30", "#C9A24B", "#D5B78A", "#5A0F1C")
    if phase not in PHASES:
        colors = ("#D5B78A",) * 4
    else:
        active = PHASES.index(phase)
        colors = tuple(
            "#9B1B30" if index == active else colors[index]
            for index in range(len(PHASES))
        )
    stops = []
    for index, color in enumerate(colors):
        start = index * 90
        end = start + 86
        stops.append(f"{color} {start}deg {end}deg")
        stops.append(f"#F3E9D2 {end}deg {(index + 1) * 90}deg")
    gradient = ", ".join(stops)
    center = phase or "No phase"
    subtitle = "estimated phase" if phase else "symptom guidance"
    description = (
        f"{phase} is highlighted."
        if phase
        else "No cycle phase is estimated."
    )
    st.markdown(
        f"""
        <div class="phase-wheel"
             style="background: conic-gradient(from -45deg, {gradient});"
             role="img"
             aria-label="Four-part cycle phase wheel. {description}">
          <div class="phase-wheel-center">{center}<small>{subtitle}</small></div>
        </div>
        <div class="phase-legend">
          {''.join(f'<span class="{"active" if phase == name else ""}">{name}</span>' for name in PHASES)}
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.caption(
        "Four equal visual sections for orientation only; this wheel is not "
        "a time-scale or fertility chart."
    )


def show_dashboard(account, profile: dict, checkin: dict) -> None:
    unsure = profile.get("cycle_date_unsure", False)
    last_period_raw = profile.get("last_period_start")
    last_period = (
        date.fromisoformat(last_period_raw)
        if last_period_raw and not unsure
        else None
    )
    cycle_length = profile.get("cycle_length")
    prediction = predict_cycle(
        today=TODAY,
        last_period_start=last_period,
        cycle_length=cycle_length,
        unsure=unsure,
    )
    safety = evaluate_safety(
        today=TODAY,
        last_period_start=last_period,
        flow=checkin["flow"],
        pain=checkin["pain"],
        severe_pain=checkin["severe_pain"],
        persistently_irregular_cycles=checkin["persistently_irregular_cycles"],
        positive_pregnancy_test=checkin["positive_pregnancy_test"],
    )

    with st.sidebar:
        st.caption("Signed in with your private code.")
        if st.button("Sign out"):
            for key in (
                "account_id",
                "flow_step",
                "voice_transcript",
            ):
                st.session_state.pop(key, None)
            st.rerun()
        if st.button("Edit today's check-in"):
            st.session_state["flow_step"] = "checkin"
            st.rerun()

    st.title("Your Phase dashboard")
    st.caption("Your reported state leads. Phase is a starting prior.")
    st.caption("Informational, not a diagnosis.")
    today_tab, workout_tab, grocery_tab, how_tab = st.tabs(
        ("Today", "Workout", "Groceries", "How this works")
    )

    with today_tab:
        st.subheader("Where you are")
        phase_wheel(prediction.phase)
        if prediction.phase is None:
            st.info(prediction.reason)
        else:
            st.subheader(f"Estimated phase: {prediction.phase}")
            st.write(f"Confidence: {prediction.confidence:.0%}")
            if prediction.population_default:
                st.info("Cold start: using a population-default 28-day cycle estimate.")
            st.write(prediction.reason)
            if prediction.fertile_window:
                start_day, end_day = prediction.fertile_window
                st.caption(
                    f"Estimated fertile window: cycle days {start_day} to {end_day}, "
                    "low confidence. Never use this estimate for contraception."
                )
        st.markdown("#### Today's check-in")
        st.write(
            f"Mood: {checkin['mood']}  |  Energy: {checkin['energy']}/5  |  "
            f"Sleep: {checkin['sleep_hours']:g} hours  |  Pain: {checkin['pain']}/10"
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
        st.subheader("Workout plan")
        if safety.suppress_plan:
            st.info("A workout plan is not shown while a safety trigger is active.")
        else:
            plan = build_plan(
                phase=prediction.phase,
                goal=profile["goal"],
                exercises=profile.get("exercises", []),
                energy=checkin["energy"],
                sleep_hours=checkin["sleep_hours"],
                pain=checkin["pain"],
            )
            st.markdown(f"### {plan['title']}")
            st.write(
                f"{plan['exercise']}: {plan['sets']} sets of {plan['reps']}."
            )
            st.write(f"Confidence: {plan['confidence']}")
            st.write(f"Reason: {plan['reason']}")
            st.caption(
                "Reason source: today's self-reported state and this low-confidence "
                "phase estimate. Research citations are not connected yet."
            )
            if prediction.phase:
                locked = get_phase_lock(
                    database.phase_locks,
                    account["_id"],
                    prediction.phase,
                )
                if locked:
                    st.success(
                        f"Your {prediction.phase}-keyed plan is locked for four "
                        "weeks. Today's reported state still takes priority."
                    )
                else:
                    week = st.selectbox(
                        "Week to save",
                        (1, 2, 3, 4),
                        key="workout-heart-week",
                    )
                    if st.button("Heart this workout", key="heart-workout"):
                        add_phase_heart(
                            database.hearts,
                            account["_id"],
                            prediction.phase,
                            "workout",
                            week,
                        )
                        st.rerun()
                    total_hearts = count_phase_hearts(
                        database.hearts,
                        account["_id"],
                        prediction.phase,
                    )
                    st.caption(
                        f"{total_hearts} of 4 hearts saved for this phase."
                    )
                    if total_hearts >= 4 and st.button(
                        "Lock my 4-week plan",
                        key="lock-workout-plan",
                    ):
                        lock_phase_plan(
                            database.phase_locks,
                            account["_id"],
                            prediction.phase,
                            plan,
                            grocery_list(
                                prediction.phase,
                                profile["dietary_preference"],
                            ),
                        )
                        st.rerun()

    with grocery_tab:
        st.subheader("Grocery list")
        if safety.suppress_plan:
            st.info("A grocery plan is not shown while a safety trigger is active.")
        else:
            items = grocery_list(
                prediction.phase,
                profile["dietary_preference"],
            )
            for item in items:
                st.checkbox(item, key=f"grocery-{account['_id']}-{TODAY}-{item}")
            st.caption("No calories, macros, or weight-loss targets.")
            if prediction.phase:
                locked = get_phase_lock(
                    database.phase_locks,
                    account["_id"],
                    prediction.phase,
                )
                if locked:
                    st.success(
                        f"The {prediction.phase}-keyed grocery list is included "
                        "in your four-week lock."
                    )
                else:
                    week = st.selectbox(
                        "Week to save",
                        (1, 2, 3, 4),
                        key="grocery-heart-week",
                    )
                    if st.button("Heart this grocery list", key="heart-grocery"):
                        add_phase_heart(
                            database.hearts,
                            account["_id"],
                            prediction.phase,
                            "grocery",
                            week,
                        )
                        st.rerun()
                    total_hearts = count_phase_hearts(
                        database.hearts,
                        account["_id"],
                        prediction.phase,
                    )
                    st.caption(
                        f"{total_hearts} of 4 hearts saved for this phase."
                    )
                    if total_hearts >= 4 and st.button(
                        "Lock my 4-week plan",
                        key="lock-grocery-plan",
                    ):
                        plan = build_plan(
                            phase=prediction.phase,
                            goal=profile["goal"],
                            exercises=profile.get("exercises", []),
                            energy=checkin["energy"],
                            sleep_hours=checkin["sleep_hours"],
                            pain=checkin["pain"],
                        )
                        lock_phase_plan(
                            database.phase_locks,
                            account["_id"],
                            prediction.phase,
                            plan,
                            items,
                        )
                        st.rerun()

    with how_tab:
        st.subheader("How this works")
        st.write(
            "Phase-based training evidence is limited. A phase estimate is only "
            "a starting prior; your reported sleep, pain, energy, and symptoms lead."
        )
        st.write(
            "Phase estimates are not a contraceptive method. The fertile-window "
            "estimate is especially uncertain."
        )
        st.write(
            "The cycle phase and plan reasons currently use deterministic local "
            "logic. Cited medical, Ayurvedic, and TCM knowledge entries are not "
            "connected in this prototype."
        )
        st.write(
            "Your account stores the salted, keyed hash of your sign-in code, "
            "profile settings, and check-in values in MongoDB. Audio is not saved."
        )


st.warning(
    "Prototype only. Not verified on a real iPhone. Use synthetic test data. "
    "No name, email, or phone number is collected."
)

mongo_uri = os.getenv("MONGODB_URI", "").strip()
database_name = (os.getenv("MONGODB_DATABASE") or "phase").strip() or "phase"
if not mongo_uri:
    st.title("Phase")
    st.error(
        "Account storage is not configured. Set MONGODB_URI in "
        "apps/web/.env, then restart Streamlit."
    )
    st.stop()

try:
    database = connect_database(mongo_uri, database_name)
except PyMongoError:
    st.title("Phase")
    st.error(
        "Could not connect to MongoDB. Check the connection string, database "
        "network access, and credentials in apps/web/.env. No account data was "
        "loaded."
    )
    st.stop()

if "account_id" not in st.session_state:
    if "pending_login_code" in st.session_state:
        show_recovery_code()
    else:
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
if profile is None or st.session_state.get("flow_step") == "profile":
    show_profile_setup(account)
    st.stop()

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
