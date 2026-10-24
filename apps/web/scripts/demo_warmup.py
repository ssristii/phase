"""Warm provider-cached content for the demo account."""

from __future__ import annotations

import os

if os.getenv("DEMO_MODE", "").strip().lower() not in {"1", "true", "yes", "on"}:
    raise SystemExit("Set DEMO_MODE=1 before running warm-up.")

print("Demo warm-up placeholder: call the live Gemini endpoints here.")
