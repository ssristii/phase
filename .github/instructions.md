# Phase project instructions

## Project summary

Phase is a cycle-aware workout and grocery planning app. The current hackathon
prototype is browser-first with Streamlit to avoid shared-Wi-Fi device
isolation; native iPhone delivery is deferred. The user's reported state takes
priority over cycle phase. Predictions include confidence and a reason; the app
is informational and not a diagnosis.

## Stack

- Streamlit and Python for the current browser prototype.
- MongoDB for account and check-in persistence; existing Express server for
  server-side sponsor integrations.
- Native iPhone app deferred; no Android build.
- Keep API keys on the server. Do not put keys in browser-visible configuration.

## Product and safety rules

- No emojis in UI, generated text, prompts, docs, or demo materials.
- Collect no name, email, or phone number. Store only a salted hash of the
  one-time 10-character login code. Tell users that a lost code means lost data.
- Do not store audio or raw transcripts. Show the transcript, allow correction,
  extract only needed fields, remove names from stored text, and discard the
  audio and raw transcript. Never log health data.
- Every prediction must show confidence and a one-sentence reason. Keep the
  footer text: "Informational, not a diagnosis."
- Suppress plans and show a clinician banner for no period in 90+ days, very
  heavy bleeding, severe pain, persistently short or long cycles, or a positive
  pregnancy test.
- Do not provide calorie deficits, weight-loss targets, moralizing food language,
  or any implication that cycle phase can be used for contraception.
- Ayurveda and TCM content is food and lifestyle guidance only: no herbs,
  supplements, or dosing. Cite knowledge-base entries and evidence labels.
- The user's logged sleep, pain, energy, and symptoms override the phase prior.
- Do not claim a feature is done unless it is documented in `docs/VERIFIED.md`
  after confirmation on a real iPhone.

## Scope and cut ladder

Build only the MVP described in the project brief. If time runs over, cut in this
order:

1. Moss: use local lookup and make no Moss claim.
2. Workout logger polish: keep set logging and rest timer only.
3. Meal prep ideas: keep the grocery list only.
4. Clinician PDF styling: plain layout is acceptable.
5. Voice readback via Sonic: keep live transcript and extraction.
6. Partner brief.

Never cut the voice check-in, cycle engine, cited phase-aware plan, hearts,
seeded demo account, safety banner, no-emoji rule, or `docs/VERIFIED.md`.

## Sponsor SDK requirements

Before using Cartesia, Gemini, or Moss SDKs, read the corresponding sponsor
documentation pasted into `docs/vendor/`. Quote the exact relied-on API signature
in a code comment. Do not guess APIs or claim an integration without verification.
