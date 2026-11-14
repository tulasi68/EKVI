# MedView PACS Benchmark

Synthetic project for calibrating claims C1–C23 (STRAT §17, §21).

## Design rules

- All identifiers, product details and defects are fictional.
- Planted cases isolate individual claims (see strategy document Cases A–O).
- Ground truth is locked *before* running the tool; never tune the corpus to match tool output.
- A held-out portion is reserved for Stage 7 red-team / repeatability.

## Current seed

`scripts/seed_medview_pacs.py` creates a minimal set of requirements corresponding to Cases A, B, C, E, G.

Full corpus (30–40 requirements, 40–60 test cases, 10–15 defects) is to be authored as part of the 90-day plan.
