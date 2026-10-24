# Phase agent guide

## Project summary

Phase is an iPhone app that adapts workouts and groceries to a user's cycle and
reported daily state, with cited advice and clear safety limits.

## Stack

Expo, React Native, TypeScript, Expo Router, Expo Go on iPhone, and either a
small Express server or Supabase Edge Functions. Use `expo-print` for PDFs.
There is no web build.

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
- Stop at each human checkpoint and provide exact iPhone test instructions.

## Cut ladder

Cut in this order: Moss (local lookup, no claim); workout logger polish (keep
sets and rest timer); meal prep ideas (keep grocery list); clinician PDF styling
(plain layout); Sonic readback (keep live transcript and extraction); partner
brief. Never cut the voice check-in, cycle engine, cited phase-aware plan,
hearts, seeded demo account, safety banner, no-emoji rule, or `docs/VERIFIED.md`.
