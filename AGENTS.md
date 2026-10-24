# Phase agent guide

## Project summary

Phase is a cycle-aware workout and grocery planner. The hackathon prototype is
browser-first with Streamlit to avoid shared-Wi-Fi device isolation; native
iPhone delivery is deferred.

## Stack

Streamlit and Python for the current browser prototype, MongoDB for account and
check-in persistence, and the existing localhost Express server for sponsor
integrations. Keep database credentials and API keys out of the browser. Native
mobile delivery is deferred.

## Non-negotiable rules

- No emojis anywhere.
- Follow the privacy, health-safety, and product rules in
  `.github/instructions.md`.
- Do not claim any feature is done unless it is in `docs/VERIFIED.md` and the
  user confirmed it on a real iPhone.
- Never use a sponsor SDK until its documentation is in `docs/vendor/` and has
  been read. Quote the relied-on signature in a code comment.
- Keep the main branch runnable. Commit each completed task with a short,
  lowercase commit message.
- At browser checkpoints provide exact browser test instructions. Never claim
  browser testing as real-iPhone verification.

## Cut ladder

Cut in this order: Moss (local lookup, no claim); workout logger polish (keep
sets and rest timer); meal prep ideas (keep grocery list); clinician PDF styling
(plain layout); Sonic readback (keep live transcript and extraction); partner
brief. Never cut the voice check-in, cycle engine, cited phase-aware plan,
hearts, seeded demo account, safety banner, no-emoji rule, or `docs/VERIFIED.md`.
