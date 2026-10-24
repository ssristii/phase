# Phase product brief

## Product intent

Phase is designed to help adults connect their cycle history and daily
self-reported state to a practical training plan. Cycle timing is a starting
estimate; sleep, energy, pain, and symptoms should lead daily adjustments.
Recommendations should be short, sourced, and clearly distinguish observed
information from generated suggestions.

## Intended onboarding

Collect only:

- Age, with an 18+ account gate
- Workouts per week, from one to seven
- Usual training split
- Training goal: Strength, Muscle, Endurance, General fitness, or Energy
- Last period start, symptom-based mode, or hormonal-contraception mode

Do not collect contact details or user-selected exercises.

## Intended daily flow

1. Record a voice or tap-based check-in.
2. Review and edit extracted values before saving.
3. See today's state and an adjusted training session.
4. Browse the training week, a meal-prep idea, sourced guidance, and a
   self-reported appointment report.

## Current repository state

The runnable browser interface is Streamlit in `apps/web/streamlit_app.py`.
An Expo screen in `apps/mobile/app/index.tsx` is a voice integration probe, not
the complete product. The provider API is Express in `apps/api/src`. This
repository does not currently contain a React/Vite PWA. See
[`AUDIT.md`](./AUDIT.md) for implementation gaps and estimates.

Only functionality the user confirms on a real iPhone belongs in
[`VERIFIED.md`](./VERIFIED.md). Automated tests and browser previews do not
count as real-device verification.
