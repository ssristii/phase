# Phase requirements audit

**Audit basis:** repository source and documentation as they exist at commit
`e1f1ee4`, reconciled against the latest Cadence requirements. No behavior is
inferred from plans or earlier summaries. The only real-device verification
recorded in `docs/VERIFIED.md` is
“None yet.”

**Time estimate:** the latest requirements add substantial model, Gemini,
statistics, PDF, seeded-demo, and provider-validation work. The previous
36–48-hour estimate is no longer sufficient; a rough remaining estimate is
50–70 focused engineering hours, before real-iPhone validation and live
provider calls. This exceeds the stated 12–16-hour window. The accepted stack
remains Streamlit plus the existing Expo probe and Express API; React/Vite PWA
requirements remain out of scope.

Severity: **P0** breaks the required demo or disqualifies a required track;
**P1** materially weakens a required product or track; **P2** is polish that
should be deferred to the backlog.

| Area | Current state from code | Gap | Severity | Fix | Estimate | Status |
|---|---|---|---|---|---:|---|
| Stack and runnable app | Browser UI is Streamlit (`apps/web/streamlit_app.py`); there is also an Expo shell whose only screen is a record/upload voice smoke test (`apps/mobile/app/index.tsx`). The API is Express (`apps/api/src`). | No React/Vite PWA, install flow, production mobile-first app, or hosted HTTPS experience. The user selected keeping the current stack, so PWA-specific requirements are explicitly not met. | P0 | Keep Streamlit and Expo; do not migrate frameworks. Preserve the local browser app and adapt features within the existing apps. Do not claim PWA installability, web production, or PWA track proof. | 0h migration; remaining feature work still applies | Accepted scope limitation |
| Onboarding and age gate | Account creation collects age; under-18 submissions are rejected before `create_account`. Versioned profile setup now collects tracking mode/date, workouts per week, split, and the five requested goals. | No separate under-18 block screen. Existing account data is not migrated/deleted in MongoDB; old users are prompted to re-enter profile settings. | P0 | Add a polite block screen and test that no account is created for minors; plan explicit legacy-data cleanup. | 1–2h | Partial |
| Authentication and recovery | A one-time 10-character code is salted and hashed with PBKDF2-HMAC-SHA256 (200,000 iterations). Sign-in scans accounts. | Spec calls for argon2id or bcrypt, rate limiting/lockout, copy and backup file, two-device recovery behavior, and iOS storage-eviction handling. No identifier-payload test exists. | P1 | Add an approved password-hash implementation, throttling and lockout, backup/export, and auth/privacy tests; do not log health values or identifiers. | 3–5h | Not started |
| Voice/audio check-in (G1) | Streamlit records then uploads through Cartesia transcription; user can edit the transcript and ask Gemini to extract structured fields. Expo is also record-then-upload. Clear is inside the transcript card immediately above the recorder; it removes transient transcript, extraction, confirmation and audio state, then rotates the recorder key. | Browser confirmation of recording, Clear, and a second recording at desktop and phone widths is pending. Gemini receives transcript text, not audio. Cartesia is not live-streamed; no AudioWorklet/PCM pipeline, name stripping, or no-double-submit guard. | P0 | Complete the desktop and phone-width Clear/re-record check. Implement the remaining G1/audio requirements separately using vendor docs. | 5–8h remaining voice | Clear implementation done; browser check pending; G1 not implemented |
| Cartesia and Sonic | The API has a Cartesia STT route and fixed-phrase Sonic readback route; both use server-side credentials. The mobile shell can play the test readback. | No full-app live partial transcript, user-specific spoken G2 readback, timeout-to-text behavior, 3-second playback fallback, reconnection behavior, or real-device pass. | P0 | Integrate documented live STT and readback into the chosen app; keep record/upload explicitly labeled as fallback. Validate key isolation and provider errors. | 3–5h | Not started |
| Gemini architecture and decisions | `apps/api/src/app.ts` calls Gemini for a hello check and transcript-to-fields extraction. The extraction validates a schema and retries malformed output once. | No central Gemini client, model config/fallback, grounded outputs, call map G1–G10, generated workouts/meals/advice, interpretation, planning decisions, caching, blocklists, injection tests, or payload identifier firewall. Only check-in extraction is implemented. | P0 | Consolidate all calls behind a server module; implement only required G1–G10 calls using current vendor documentation, schema validation, retry/fallback, caching, content filters, and request-inspection tests. | 7–10h | Not started |
| Cycle model (M1) | `apps/web/phase_engine.py` still has a deterministic 28-day-default phase calculation and internal confidence/fertile-window values; the Streamlit UI no longer displays those values. | No online Bayesian cycle-length or bleed-length estimation, forgotten weighted observations, predictive interval, inferred period starts, missing-log flags, learned uncertainty mode, or statistical tests. | P0 | Implement the specified configurable Normal-Inverse-Gamma posterior, cycle detection, symptom-mode threshold, and deterministic fixtures. | 5–7h | Not started |
| Readiness model (M2) | Today’s workout adjustment is a fixed heuristic based on sleep, pain, and energy. | No online logistic regression, phase features, rating feedback, per-account versioned weights, reset, or isolation tests. | P0 | Implement per-user prior/update/clipping and rating flow; test numerical gradients, synthetic convergence, persistence isolation, and reset. | 4–6h | Not started |
| Workout generation and logging (G3/G4) | A deterministic seven-day template now uses workout frequency, split, and goal; today may be adjusted from the check-in. It is labeled as a template. Four distinct phase hearts can persist a phase-keyed template and lock the saved plans. There is no workout logger. | No Gemini-generated plan with validated exercise IDs/sets/rest, bounded retry/template fallback, learned readiness scaling, set logger, rest timer, completion rating, or unheart action. | P0 | Add a licensed exercise dataset after verifying its license; implement validated G3/G4 generation and fallback, logger, ratings, and heart removal. | 6–9h | Partial |
| Meals (G5) | The grocery generator and grocery UI have been removed. Meals is an empty screen; no generated item is stored. | No grounded, daily meal-prep idea, source, cache, retrieval date, duplicate-title guard, or yesterday history exists. | P1 | Implement one grounded, cached meal idea per day with validated source and allergy reminder; only show generated or cached items, otherwise empty state plus retry. | 3–5h | Not implemented |
| “What might help” (G6/G7) | No knowledge/help tab or evidence entries are connected. `docs/VERIFIED.md` says Moss is not used. | No phase/lens/symptom UI, sourced grounded entries, evidence labels, source allowlist, retrieval dates, cache, or G7 daily pick. | P1 | Implement current-phase-first grounded guidance and citation validation; use local lookup if Moss misses its timebox and make no Moss claim. | 4–6h | Not started |
| Escalation and safety | Existing code suppresses plans for no period at 90 days, very heavy flow, severe pain/pain >= 8, self-reported irregular cycles, or positive pregnancy test. | No pain >= 8 twice in three days, heavy flow three consecutive days, or 3-of-4 short/long cycle detector. Threshold logic is not fully history-backed or exhaustively tested; symptom mode is not implemented. | P0 | Implement the exact history-based fixed triggers and pain override; make every escalation suppress generated plans; add one test per trigger and combination. | 2–4h | Not started |
| Clinician report and statistics (G8) | No report or PDF exists. | Missing computed statistics, cycle-length chart, flags, generated narrative, “Self-reported data” label, PDF export, iOS share and fallback. | P1 | Add deterministic `stats.py` with specified formulas and hand-computed fixtures; build a PDF with computed stats only; never use Gemini to calculate statistics. | 5–7h | Not implemented |
| Partner brief | No partner brief or share flow exists. | Missing generated plain-language brief, identifier exclusion, preview, and explicit user-tap sharing. | P1 | Implement schema-validated brief, preview, and user-initiated share only; do not send identifiers. | 1–2h | Not started |
| Navigation and required screens | Streamlit now has five tabs: Today, Train, Meals, What might help, and Report. Train contains the current template; Meals, help, and report are explicit placeholders. | No bottom navigation; the check-in confirmation screen, meal/help content, and report are incomplete. | P0 | Fill the required destinations using Streamlit tabs and the existing Expo shell where reachable; bottom-navigation/PWA behavior is out of scope under the selected stack. | 3–5h | Partial |
| Transcript clear control | Streamlit offers “Clear voice text” after transcript creation; the control is in a two-column area and is absent before text exists. | Does not meet the always-visible 44px Clear control, empty-state treatment, audio-buffer discard, and restart-listening behavior. | P1 | Keep an accessible Clear control visible at all times and test empty/nonempty transcript and audio cleanup. | 1–2h | Not started |
| Copy and prohibited language | The Streamlit UI no longer displays confidence or fertile-window values; the Expo footer and “How this works” tab were removed. Grocery UI/profile fields and the old SQL columns were removed. | Internal cycle-model metadata remains intentionally internal. There is no app-wide test for every possible screen, generated response, report, or README (those features are not implemented). | P0 | Keep the scoped static copy test and extend it as generated content and report screens are added. | Ongoing | Partial |
| Visual design and accessibility | The Streamlit theme uses the prior “Victorian Gilt” palette, serif type, raised buttons, and styled phase wheel. | Does not match the new UI tokens or React PWA screen frame, ornaments, bottom navigation, Luna, pressed flowers, specified cards/chips, Nunito, reduced-motion behavior, or verified WCAG AA contrast. | P1 | Apply the exact current UI spec to all required screens, bundle fonts/illustrations, and test 390x844 plus contrast and reduced motion. | 5–8h | Not started |
| Storage, cache, and privacy | MongoDB persistence stores an account hash/profile/check-ins, plus hearts and locks. Voice text is kept in Streamlit session state until cleared/submission. | No retention policy, generated-content cache, retrieval timestamps, per-user learned weights, age/workout split schema, outgoing-payload audit, name stripping, or health-log grep test. The standalone SQL schema is inconsistent with the MongoDB implementation. | P1 | Define and document stored fields/retention; migrate schema deliberately; add no-health-logs and no-identifier-payload tests. | 2–4h | Not started |
| Seed/demo flow | No seeded demo account or synthetic history/replay/reset flow is present in the audited app. | Required deterministic 90-day history, M1/M2 replay, script-today fixture, safety assertions, labeled demo account, four-phase heart state, gated controls, and warm-up run are missing. | P0 | Add deterministic synthetic generator and isolated demo persistence, replay fitted models, test fixture invariants and controls hidden unless `DEMO_MODE=1`; add provider warm-up script after calls exist. | 5–8h plus live API warm-up | Not implemented |
| Tests and quality gates | Python unit tests cover basic cycle rules, safety examples, exercise validation, schedule, groceries, account hashing, and hearts. API tests cover health, missing keys, and audio content types. | No model-specific fixtures, LLM call mocks/fallbacks, injection/blocklist/citation checks, escalation history cases, banned-copy scan, logger/report/privacy/PWA tests, or complete iPhone run. | P0 | Add tests from the supplied test matrix as features are implemented; run provider smoke tests only with user-approved secrets and inspect payloads without exposing health text. | 4–7h | Not started |
| Documentation, claims, and submissions | `docs/VERIFIED.md` correctly has no iPhone-confirmed features; setup/problem docs describe the old prototype. There is no thorough README, AUDIT, SUBMISSION, architecture diagram, or claims audit. | Documentation is stale and describes removed features; there is no substantiation for sponsor tracks, metrics, community, quote, production setup, or submission proof. | P1 | Document actual implementation after code changes; map each public claim to `VERIFIED.md`; omit unverified tracks and metrics. Obtain community/quote only when needed. | 3–5h | Not started |
| Deployment and connectivity | API is bound to `127.0.0.1`; browser instructions explicitly keep it local. No deployed PWA URL/domain is present in verified docs. | No HTTPS custom domain, `www` redirect, cellular certificate test, warm-up plan, or phone-accessible production deployment. Shared Wi-Fi previously prevented LAN phone testing. | P1 | Deploy only after auth/security review; configure domain/HTTPS and test from cellular. Never expose the local unauthenticated API or MongoDB URI. | 2–4h | Not started |
| Sponsor and track eligibility | Cartesia and Gemini notes are in `docs/vendor`; Moss is explicitly marked unused in `docs/VERIFIED.md`. | Live Cartesia streaming and visible Sonic, essential Gemini G1–G10, Microsoft vendor review, GoDaddy domain proof, and all real-device pass conditions are absent. No Microsoft vendor document exists in `docs/vendor`. | P0 | Verify official vendor docs before implementation; omit any track without matching verified proof. Ask for the named community and real quote before claiming social-impact eligibility. | 2–4h plus external confirmations | Not started |

## P2 deferred to backlog

- Decorative Luna expressions, animated waveform, six-star heart burst, and
  other ornamental motion beyond the accessible baseline.
- Prefetch all 12 phase/lens help sets; fetch the current phase first and defer
  the remaining sets until core caching and validation work.
- Fine-grained PDF visual polish after statistics, export, and iOS sharing work.
- Extra training-plan visual polish after generated-plan validation and workout
  logging are reliable.

## Accepted implementation direction

The user selected **keep the current stack**. The product remains a Streamlit
browser app with an Expo voice-test shell and Express API. This honors “do not
rebuild or restructure” but knowingly leaves the React/Vite PWA, installability,
safe-area implementation, and PWA deployment requirements unmet. The local
Streamlit app remains the primary runnable demo; no PWA claims will be made.

## Phase 1 result

- **Done:** audited the checked-in implementation and documented concrete gaps,
  severity, fixes, estimates, and the P2 backlog.
- **Risky:** the adaptable scope is estimated at 36–48 focused hours versus the
  12–16 hours available; P0 work alone is larger than the remaining window.
- **Cut:** React/Vite PWA migration, installability, and PWA-specific proof are
  out of scope by the user's stack decision. Moss remains unused; the supplied
  new spec's never-cut requirements conflict with the previous hackathon cut
  ladder, so the new spec is treated as controlling.

## Phase 2 progress: onboarding and template schedule

- Replaced profile exercise/diet fields with cycle tracking mode, optional
  period date, workouts per week, training split, and the five allowed goals.
  Existing profiles with an older version are asked to complete setup again.
- Rebuilt the seven-day deterministic template to honor the chosen weekly
  frequency and split. It is visibly labeled as a template, not AI output.
- Removed the grocery pathway and its schema fields; added explicit
  not-connected placeholders for meals, sourced guidance, and report rather
  than presenting static content as generated or cited.
- Removed the phase wheel when cycle timing is hidden, removed displayed
  confidence/fertility values and prohibited disclaimer/footer copy, and made
  transcript clearing visible even before a transcript exists.
- Updated versioned profile, split-schedule, phase-heart/lock, schema, and
  prohibited-copy tests. Python tests pass; API tests/typecheck pass; the SQL
  schema executes in SQLite. Full Expo typechecking remains blocked because
  the mobile manifest does not declare the imported Expo Router/audio/filesystem
  packages; TSX syntax validation passes. Restoring declared mobile packages
  also reported five high-severity npm advisories; they were not triaged in
  this feature slice.
- **Done:** this implementation slice is committed separately from the audit.
- **Risky:** full Gemini workout generation, learned models, real-time voice,
  meal/help generation, and the statistics report remain unimplemented.
- **Cut:** no never-cut feature is intentionally removed; PWA migration remains
  outside the accepted stack direction.

## Latest requirements audit addendum

The user's newest Cadence specification supersedes the prior presentation-only
limit and the former fallback-text preference. Logic and Gemini calls may now
be changed. The earlier Step 2 profile and template work remains the actual
code; it is not evidence that the remaining steps are implemented.

| Step | Current state | Gap / severity | Fix and estimate | State |
|---|---|---|---|---|
| 1 Clear placement | Clear now appears in the transcript card immediately before the recorder. The recorder key uses `audio_{nonce}`; Clear removes transcript, extraction, confirm-state and temporary audio values before incrementing the nonce and rerunning. | P0: browser recording/reset/re-record behavior has not yet been verified by the user at both required viewport sizes. | Keep the nonce-keyed reset, automated regression checks, and user browser verification for first recording, Clear, and second recording. | Implemented; awaiting browser check |
| 2 M1/M2 models | No `models.py`; current phase engine uses deterministic heuristics and no stored readiness weights. | P0: both required per-user models absent. | Implement configured NIG cycle/bleed posteriors, detection, uncertainty mode, feature encoding, online logistic updates, per-user versioned SQLite storage/reset, and fixture tests. 10–14h. | Not implemented |
| 3 Gemini client | One Gemini extraction endpoint exists; it accepts transcript text and does not centrally implement G1–G10. | P0: no shared pydantic schemas/client, grounding, identifier firewall, retry/fallback/cache/blocklist coverage, or calls G1–G10. | Read vendor docs per operation; centralize models and schemas, prompt delimiters, timeout/retry/cache, output filters, and payload tests. 8–12h. | Not implemented |
| 4 Audio | Cartesia batch STT and a fixed TTS probe exist; Streamlit is explicitly record-then-upload. | P0: Gemini does not understand audio directly; live transcript, confirm provenance, G2 readback, runtime fallback, and name stripping absent. | Keep the existing documented fallback honest unless supported PCM streaming is verified; implement approved G1/G2 audio understanding and editable confirmation. 5–8h. | Not implemented |
| 5 Workouts | Seven-day deterministic plan uses frequency, split and goal; no logger. | P0: no 150-entry licensed exercise set, G3/G4 generation/validation, readiness scaling, logger/rating. | Verify dataset license, implement generated plan validation/fallback, apply M2/G4, and add logger/timer/rating. 8–12h. | Partial |
| 6 Stats/PDF | No statistics module, computed report, or PDF. | P1: report requirement wholly absent. | Compute exact formulas with `statistics`/`numpy`, tests, chart and PDF built from stats, safe empty state. 5–7h. | Not implemented |
| 7 Meals | Empty state only; grocery feature was removed. | P1: G5, grounding, cache/duplicate/heart/history, retry absent. | Implement grounded schema-validated meal idea and daily cache; never provide hand-written replacement content. 3–5h. | Not implemented |
| 8 What might help | Empty state only; no advice knowledge items. | P1: G6/G7 UI, allowlist, evidence, retrieval date, cache, and ID validation absent. | Implement grounded current phase/lens guidance, allowlisted citations, validated cache, and G7 choice by item ID. 5–8h. | Not implemented |
| 9 G8/G9/G10 | None of narrative, partner brief, or weekly insight exists. | P1/P2: no number grounding, preview/share, or trend-only insight. | Add schema-validated calls after stats and interaction data; partner brief is cut first if time is short. 3–5h. | Not implemented |
| 10 Seeded run | No demo fixture or model replay. | P0: central demo path absent. | Generate deterministic 90-day data and replay M1/M2 in isolated demo account; test ranges, safety, reset and scripted today. 5–8h. | Not implemented |
| 11 Demo controls | No `DEMO_MODE` controls. | P1: cannot perform seeded demo flow/reset or banner simulation. | Add gated demo controls only after seed runner exists; test controls absent by default. 1–2h. | Not implemented |
| 12 Warm-up | No provider warm-up script. | P1: caches cannot be prewarmed and no real Gemini calls have been smoke-tested. | Add idempotent, fail-fast warm-up only after all named call schemas and caches exist. 1–2h plus provider latency. | Not implemented |
| 13 Tests | 22 Python tests passed before this addendum; existing tests cover basic rules, not the supplied full matrix. | P0: no M1/M2, grounded Gemini, report/PDF, seed, escalation-history, or full privacy test matrix. | Add tests alongside each implementation; do not claim live provider calls from mocks. 6–10h. | Partial |
| 14 Recording runbook | No `docs/DEMO_RECORDING.md`. | P2 until working end-to-end build exists. | Document only verified working flow after demo warm-up. 1h. | Not implemented |
| 15 README / completion | README absent; verified file says no real iPhone tests. | P1: no implementation-derived docs or honest completion table. | Document actual code and verified claims after implementation; do not write success claims for untested calls. 3–5h. | Not implemented |

- **Risky:** realistic remaining work exceeds the hackathon time budget. No live
  Gemini calls, real audio-understanding run, PDF export, learned-model replay,
  or complete phone flow has been verified.
- **Cut:** partner brief, PDF styling, background prefetch, meal hearts, Moss,
  mascot animation, and non-current help-set prefetch are cut first. Required
  M1/M2, stats/PDF contents, meals, current help, voice understanding,
  escalation, and seeded demo remain.

## Step 1 progress: recorder Clear/reset

- Read installed Streamlit 1.53.1 signatures for `st.container` and
  `st.audio_input`; the signatures relied on are quoted next to their use.
- Moved the always-visible Clear row inside the transcript card and directly
  above `st.audio_input`. The audio widget now gets a monotonically increasing
  `audio_nonce` key. Clear also removes transcript, extracted values,
  confirmation state, WAV bytes and upload state before rerunning.
- Check-in submission and sign-out also discard the current temporary audio
  capture; successful transcription resets the recorder while retaining only
  the editable transcript.
- **Automated results:** `python -m unittest discover -s apps\web -p
  "test_*.py"` passed 23 tests; `python -m py_compile
  apps\web\streamlit_app.py` passed; `git diff --check` passed.
- **Done:** implementation and regression checks.
- **Risky:** recording, clear, and a second recording need confirmation in the
  browser at desktop and phone widths.
- **Cut:** no Clear behavior was cut; live streaming is not implemented by
  this recorder and remains an honest record-then-upload flow.
