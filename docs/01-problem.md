# Phase: problem and MVP plan

**Problem.** People who track cycles often have to translate a cycle date and
today's symptoms into workout and grocery choices themselves. Generic plans
miss the user's current state; cycle-based advice can overstate limited evidence.
Phase treats cycle phase as a starting prior, lets reported state take priority,
and gives each recommendation a cited reason and evidence label.

**Target user.** An adult iPhone user who tracks or wants to understand their
cycle, plans exercise and groceries, and wants practical guidance without
fertility claims, weight-loss framing, or sharing identity details.

**Fields and why they exist.** Age is used only to enforce the 18+ gate. Last
period start drives the cycle estimate; “unsure” disables phase claims and
enables symptom-based guidance. Goal and up to five current exercises shape the
workout plan. Dietary preference filters the grocery list. Check-in flow supports
the heavy-bleeding safety trigger; mood supports symptom-based guidance and the
self-reported summary; energy and sleep inform session adjustment; pain informs
session adjustment and the severe-pain safety trigger; workout done measures
adherence. No name, email, phone, calories, or weight-loss target is collected.

**Three riskiest assumptions.**

1. A 60-second voice check-in is comfortable and faster than tapping, while
   editable extraction and no audio retention earn trust.
2. A cited, phase-aware plan feels useful despite limited phase-based training
   evidence, especially when symptoms override phase.
3. A one-time recovery code and anonymous, self-reported history are acceptable
   tradeoffs for not collecting contact details.

**Success metrics (proposed validation targets, not results).**

- **Check-in speed:** at least 80% of observed adults complete a voice or tap
  check-in in 60 seconds or less.
- **Plan adherence:** at least 50% of suggested weekly sessions are marked done
  by participating testers in a seven-day trial.
- **Report generated:** at least 80% of testers generate the self-reported
  clinician summary without help in two minutes or less.

**Candidate track fit** (illustrative categories; map to the event's official
track names when available).

| Candidate track | Fit | Why |
|---|---|---|
| Health and wellness | Strong | Personalized planning with explicit evidence limits and safety escalation |
| AI and voice | Strong | Voice check-in extracts structured fields for user confirmation |
| Mobile consumer product | Strong | Daily check-in, plans, and reports are designed for iPhone |

**Two-minute demo outline (planned, not verified).**

| Time | Show |
|---|---|
| 0:00–0:20 | Open the seeded synthetic profile and explain the privacy-first code |
| 0:20–0:45 | Voice check-in with transcript and editable confirmation |
| 0:45–1:10 | Show today's plan downgraded for reported sleep and pain, with cited reason |
| 1:10–1:30 | Open the cited grocery list and clinician summary |
| 1:30–1:50 | Show partner brief sharing only after a tap and hearted-plan lock |
| 1:50–2:00 | Close on “phase is a starting prior; your data leads” and safety footer |
