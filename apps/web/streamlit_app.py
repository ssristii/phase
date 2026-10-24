from datetime import date, timedelta

import streamlit as st

from phase_engine import build_plan, evaluate_safety, grocery_list, predict_cycle


st.set_page_config(page_title="Phase", page_icon=None, layout="centered")
st.markdown(
    """
    <style>
    .stApp { background: #F3E9D2; color: #2A1A14; }
    h1, h2, h3 { color: #5A0F1C; font-family: Georgia, serif; }
    div.stButton > button, div.stFormSubmitButton > button {
        background: #9B1B30; color: #F3E9D2; border: 1px solid #C9A24B;
        border-radius: 999px; padding: 0.55rem 1.2rem;
    }
    div[data-testid="stAlert"] { border-radius: 12px; }
    div[data-testid="stAlert"] p,
    div[data-testid="stAlert"] div { color: #2A1A14 !important; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("Phase")
st.caption("Your cycle is a starting prior. Your reported state leads.")
st.warning(
    "Browser prototype only. Not verified on a real iPhone. "
    "Do not enter identifying or sensitive personal information."
)
st.info("The prefilled example profile and check-in are synthetic.")
st.caption("Informational, not a diagnosis.")

today = date.today()
if "profile" not in st.session_state:
    st.session_state.profile = {
        "age": 28,
        "unsure": False,
        "last_period": today - timedelta(days=9),
        "cycle_length": None,
        "goal": "Strength",
        "exercises": ["Bodyweight squat", "Glute bridge"],
        "diet": "No preference",
    }
if "checkin" not in st.session_state:
    st.session_state.checkin = {
        "flow": "None",
        "mood": "Okay",
        "energy": 2,
        "sleep": 5.0,
        "pain": 7,
        "workout_done": False,
        "severe_pain": False,
        "irregular": False,
        "pregnancy": False,
    }
if "hearts" not in st.session_state:
    st.session_state.hearts = set()
if "locked_phases" not in st.session_state:
    st.session_state.locked_phases = set()

with st.sidebar:
    st.header("Profile")
    st.caption("No name, email, phone, or login code is requested.")
    age = st.number_input("Age", min_value=0, max_value=120, value=st.session_state.profile["age"])
    if age < 18:
        st.error("Phase is for adults 18 and older. This prototype does not continue.")
        st.stop()

    unsure = st.checkbox(
        "I am unsure of my last period start",
        value=st.session_state.profile["unsure"],
    )
    last_period = st.date_input(
        "Last period start",
        value=st.session_state.profile["last_period"],
        disabled=unsure,
    )
    use_cycle_length = st.checkbox(
        "I know my typical cycle length",
        value=st.session_state.profile["cycle_length"] is not None,
        disabled=unsure,
    )
    cycle_length = None
    if use_cycle_length and not unsure:
        cycle_length = st.number_input(
            "Typical cycle length (days)",
            min_value=21,
            max_value=35,
            value=st.session_state.profile["cycle_length"] or 28,
        )
    goal = st.selectbox(
        "Goal",
        ["Strength", "General fitness", "Energy"],
        index=["Strength", "General fitness", "Energy"].index(
            st.session_state.profile["goal"]
        ),
    )
    exercises = st.multiselect(
        "Current exercises (up to 5)",
        [
            "Bodyweight squat",
            "Glute bridge",
            "Wall push-up",
            "Dumbbell row",
            "Dead bug",
            "Step-up",
            "Hip hinge",
            "Overhead press",
        ],
        default=st.session_state.profile["exercises"],
        max_selections=5,
    )
    diet = st.selectbox(
        "Dietary preference",
        ["No preference", "Vegetarian", "Vegan", "Gluten-free"],
        index=["No preference", "Vegetarian", "Vegan", "Gluten-free"].index(
            st.session_state.profile["diet"]
        ),
    )
    st.session_state.profile = {
        "age": age,
        "unsure": unsure,
        "last_period": last_period,
        "cycle_length": cycle_length,
        "goal": goal,
        "exercises": exercises,
        "diet": diet,
    }

st.subheader("Today's check-in")
with st.form("daily-checkin-form"):
    flow = st.selectbox("Flow", ["None", "Light", "Moderate", "Heavy", "Very heavy"])
    mood = st.selectbox("Mood", ["Low", "Okay", "Good", "Anxious", "Irritable"])
    energy = st.slider("Energy", min_value=1, max_value=5, value=st.session_state.checkin["energy"])
    sleep = st.slider("Sleep (hours)", min_value=0.0, max_value=12.0, step=0.5, value=st.session_state.checkin["sleep"])
    pain = st.slider("Pain (0 to 10)", min_value=0, max_value=10, value=st.session_state.checkin["pain"])
    workout_done = st.checkbox("I completed a workout", value=st.session_state.checkin["workout_done"])
    severe_pain = st.checkbox("Pain feels severe", value=st.session_state.checkin["severe_pain"])
    irregular = st.checkbox(
        "I have persistently short (under 21 days) or long (over 35 days) cycles",
        value=st.session_state.checkin["irregular"],
    )
    pregnancy = st.checkbox(
        "I had a positive pregnancy test",
        value=st.session_state.checkin["pregnancy"],
    )
    submitted = st.form_submit_button("Save check-in")

if submitted:
    st.session_state.checkin = {
        "flow": flow,
        "mood": mood,
        "energy": energy,
        "sleep": sleep,
        "pain": pain,
        "workout_done": workout_done,
        "severe_pain": severe_pain,
        "irregular": irregular,
        "pregnancy": pregnancy,
    }

profile = st.session_state.profile
checkin = st.session_state.checkin
try:
    prediction = predict_cycle(
        today=today,
        last_period_start=profile["last_period"],
        cycle_length=profile["cycle_length"],
        unsure=profile["unsure"],
    )
except ValueError as error:
    st.error(str(error))
    st.stop()

if prediction.phase is None:
    st.subheader("Symptom-based guidance")
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

safety = evaluate_safety(
    today=today,
    last_period_start=None if profile["unsure"] else profile["last_period"],
    flow=checkin["flow"],
    pain=checkin["pain"],
    severe_pain=checkin["severe_pain"],
    persistently_irregular_cycles=checkin["irregular"],
    positive_pregnancy_test=checkin["pregnancy"],
)
if safety.alerts:
    st.error(
        "Clinician guidance recommended. Plans are suppressed for this check-in."
    )
    for alert in safety.alerts:
        st.write(f"- {alert}")

st.subheader("Workout")
plan_week = st.selectbox("Plan week", [1, 2, 3, 4])
if safety.suppress_plan:
    st.info("A workout plan is not shown while a safety trigger is active.")
else:
    plan = build_plan(
        phase=prediction.phase,
        goal=profile["goal"],
        exercises=profile["exercises"],
        energy=checkin["energy"],
        sleep_hours=checkin["sleep"],
        pain=checkin["pain"],
    )
    st.markdown(f"**{plan['title']}**")
    st.write(f"{plan['exercise']}: {plan['sets']} sets of {plan['reps']}.")
    st.write(f"Confidence: {plan['confidence']}")
    st.write(f"Reason: {plan['reason']}")
    st.caption(
        "Reason source: today's self-reported check-in and the displayed "
        "low-confidence phase estimate. Research citations are not yet wired "
        "into this browser prototype."
    )
    if prediction.phase:
        workout_key = f"workout:{prediction.phase}:week:{plan_week}"
        if st.button("Save workout plan", key=f"save_workout_{plan_week}"):
            st.session_state.hearts.add(workout_key)

st.subheader("Grocery list")
if safety.suppress_plan:
    st.info("A grocery plan is not shown while a safety trigger is active.")
else:
    items = grocery_list(prediction.phase, profile["diet"])
    st.write(", ".join(items))
    if prediction.phase:
        grocery_key = f"grocery:{prediction.phase}:week:{plan_week}"
        if st.button("Save grocery list", key=f"save_grocery_{plan_week}"):
            st.session_state.hearts.add(grocery_key)

phase = prediction.phase
phase_hearts = sum(
    1 for heart in st.session_state.hearts if phase and f":{phase}:" in heart
)
if phase:
    st.caption(f"Saved items for {phase}: {phase_hearts} of 4 required.")
    if phase_hearts >= 4:
        st.session_state.locked_phases.add(phase)
    if phase in st.session_state.locked_phases:
        st.success(
            f"Your {phase}-keyed plan is locked for four weeks. "
            "It follows the phase estimate, not the calendar day."
        )

st.subheader("How this works")
st.write(
    "Phase-based training evidence is limited. A phase estimate is only a "
    "starting prior; your reported sleep, pain, energy, and symptoms lead."
)
st.caption("This browser prototype keeps information in this browser session only.")
